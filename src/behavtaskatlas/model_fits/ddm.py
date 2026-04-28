"""Forward + fit for the vanilla DDM variant via EZ-DDM closed forms.

Diffusion coefficient s is normalized to 1; starting point z = a/2
(unbiased); drift_bias = 0; lapse = 0. Free parameters are
drift_per_unit_evidence (k), boundary (a), and non_decision_time (t0).

EZ-DDM closed forms (Wagenmakers, van der Maas, Grasman 2007):

  P(right | x)  = 1 / (1 + exp(-2 k x a))
  E[DT | x]     = (a / (2 k x)) · tanh(k x a),   x ≠ 0
  E[DT | 0]     = a² / 4
  E[RT | x]     = E[DT | x] + t0

The fit is joint over a (psychometric, chronometric) pair with the
same paper / stratification. The dispatch from cli._do_fit_one looks
up the matching chronometric by paper_id + stratification.condition;
fits with no chronometric partner are skipped at this stage (a
future variant can fit psychometric alone with t0 fixed or marginalised).

For the audit, ModelFit.predictions carries the psychometric prediction
on the psychometric finding's x grid; the chronometric prediction is
derivable from params at audit time but not stored.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize

from behavtaskatlas.model_layer import register_forward
from behavtaskatlas.models import CurvePoint, Finding

VARIANT_ID = "model_variant.ddm-vanilla"
PARAM_ORDER = ("drift_per_unit_evidence", "boundary", "non_decision_time")


def predict_p_right(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    k = params["drift_per_unit_evidence"]
    a = params["boundary"]
    return 1.0 / (1.0 + np.exp(-np.clip(2.0 * k * xs * a, -700.0, 700.0)))


def predict_mean_decision_time(
    params: dict[str, float], abs_xs: np.ndarray
) -> np.ndarray:
    k = params["drift_per_unit_evidence"]
    a = params["boundary"]
    abs_xs = np.asarray(abs_xs, dtype=float)
    out = np.empty_like(abs_xs)
    nonzero = abs_xs > 0.0
    if np.any(nonzero):
        v = k * abs_xs[nonzero]
        out[nonzero] = (a / (2.0 * v)) * np.tanh(np.clip(v * a, -50.0, 50.0))
    out[~nonzero] = (a * a) / 4.0
    return out


def predict_mean_rt(params: dict[str, float], abs_xs: np.ndarray) -> np.ndarray:
    return predict_mean_decision_time(params, abs_xs) + params["non_decision_time"]


def forward(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    """Return a predicted curve on the finding's x grid. Curve type
    decides what we predict (p_right vs mean RT). Variant-fixed
    parameters (z=0.5, drift_bias=0, lapse=0) are baked into the
    closed forms above.
    """
    xs = np.array([p.x for p in finding.curve.points])
    if finding.curve.curve_type == "psychometric":
        ys = predict_p_right(params, xs)
    elif finding.curve.curve_type == "chronometric":
        ys = predict_mean_rt(params, np.abs(xs))
    else:
        raise ValueError(
            f"DDM forward only handles psychometric or chronometric curves; "
            f"got {finding.curve.curve_type!r}."
        )
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def _joint_negative_log_likelihood(
    theta: np.ndarray,
    *,
    psy_xs: np.ndarray,
    psy_ns: np.ndarray,
    psy_ks: np.ndarray,
    chr_abs_xs: np.ndarray,
    chr_ys: np.ndarray,
    rt_sigma: float,
) -> float:
    params = dict(zip(PARAM_ORDER, theta, strict=True))
    p = predict_p_right(params, psy_xs)
    p = np.clip(p, 1e-9, 1.0 - 1e-9)
    binom = -np.sum(psy_ks * np.log(p) + (psy_ns - psy_ks) * np.log(1.0 - p))
    rt_pred = predict_mean_rt(params, chr_abs_xs)
    # Gaussian RT term with a fixed σ; trades off against the binomial
    # term so the fit doesn't ignore RT in favor of choice probabilities.
    rt = 0.5 * np.sum(((rt_pred - chr_ys) / rt_sigma) ** 2)
    return float(binom + rt)


def fit(finding: Finding, *, chronometric: Finding | None = None) -> dict[str, Any]:
    """Joint EZ-DDM fit. Requires a paired chronometric finding.

    The caller is responsible for matching the chronometric to the
    psychometric by paper / stratification; this function just runs
    the optimization on the two curves it's handed.
    """
    if finding.curve.curve_type != "psychometric":
        raise ValueError(
            "DDM fit anchors on the psychometric finding; "
            f"got {finding.curve.curve_type!r}."
        )
    if chronometric is None:
        raise ValueError(
            "DDM fit requires a paired chronometric finding; none supplied."
        )
    if chronometric.curve.curve_type != "chronometric":
        raise ValueError(
            f"Expected chronometric paired finding; got "
            f"{chronometric.curve.curve_type!r}."
        )

    psy_xs = np.array([p.x for p in finding.curve.points])
    psy_ns = np.array([p.n for p in finding.curve.points])
    psy_ks = np.array(
        [int(round(p.y * p.n)) for p in finding.curve.points], dtype=float
    )
    chr_abs_xs = np.array([abs(p.x) for p in chronometric.curve.points])
    chr_ys = np.array([p.y for p in chronometric.curve.points])

    rt_sigma = max(float(np.std(chr_ys)), 1e-3)
    x_range = max(float(psy_xs.max() - psy_xs.min()), 1e-6)
    # Initial guess: small drift per unit evidence, moderate bound, and
    # half the minimum observed RT as a starting t0.
    x0 = np.array([1.0 / x_range, 1.0, 0.5 * float(chr_ys.min())])
    bounds = [
        (1e-6, 100.0 / x_range),
        (1e-3, 10.0),
        (0.0, float(chr_ys.min())),
    ]

    def _objective(theta: np.ndarray) -> float:
        return _joint_negative_log_likelihood(
            theta,
            psy_xs=psy_xs,
            psy_ns=psy_ns,
            psy_ks=psy_ks,
            chr_abs_xs=chr_abs_xs,
            chr_ys=chr_ys,
            rt_sigma=rt_sigma,
        )

    result = minimize(
        _objective,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 1000},
    )
    log_likelihood = float(-result.fun)
    n_trials = int(psy_ns.sum())
    n_free = len(PARAM_ORDER)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)
    parameters = dict(zip(PARAM_ORDER, [float(v) for v in result.x], strict=True))

    psy_pred = predict_p_right(parameters, psy_xs)
    predictions = [
        {"x": float(x), "n": int(n), "y": float(y)}
        for x, n, y in zip(psy_xs, psy_ns, psy_pred, strict=True)
    ]
    chr_pred = predict_mean_rt(parameters, chr_abs_xs)
    chr_residual = float(np.max(np.abs(chr_pred - chr_ys)))
    quality = {
        "log_likelihood": log_likelihood,
        "aic": aic,
        "bic": bic,
        "n_trials": float(n_trials),
        "n_free_params": float(n_free),
        "chronometric_max_residual_s": chr_residual,
        "rt_sigma_assumed_s": rt_sigma,
    }
    return {
        "parameters": parameters,
        "quality": quality,
        "predictions": predictions,
        "fit_method": {
            "type": "scipy.optimize.minimize",
            "options": {
                "method": "L-BFGS-B",
                "bounds": "see code",
                "loss": "binomial NLL + Gaussian RT chi-squared",
            },
            "duration_seconds": None,
        },
        "success": bool(result.success),
        "message": str(getattr(result, "message", "")),
        "paired_chronometric_id": chronometric.id,
    }


register_forward(VARIANT_ID, forward)
