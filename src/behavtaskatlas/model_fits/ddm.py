"""Forward + fit for the drift-diffusion family.

Three variants share this implementation:

  * ddm-vanilla              free: k, a, t0           (z=0.5, v0=0)
  * ddm-starting-point-bias  free: k, a, t0, z        (v0=0)
  * ddm-drift-bias           free: k, a, t0, v0       (z=0.5)

Diffusion coefficient s is normalized to 1; lapse is fixed at 0 in
all three variants.

Closed-form choice probability with biased starting point z (fraction
of boundary, z=0.5 unbiased) and drift v = k·x + v0:

  P(upper | x) = (1 − exp(−2 v z a)) / (1 − exp(−2 v a))     v ≠ 0
  P(upper | x) = z                                            v = 0

Marginal mean decision time uses the unbiased EZ-DDM closed form with
effective drift |k·|x| + v0|; z does not enter the RT prediction in
this approximation. Caveats noted in fit metadata.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize

from behavtaskatlas.model_layer import register_forward
from behavtaskatlas.models import CurvePoint, Finding

VARIANT_VANILLA = "model_variant.ddm-vanilla"
VARIANT_Z_BIAS = "model_variant.ddm-starting-point-bias"
VARIANT_V_BIAS = "model_variant.ddm-drift-bias"

# Order matters for the optimizer: vanilla uses [k, a, t0]; z-bias adds
# starting_point; v-bias adds drift_bias. A variant's free_parameter
# list (from the YAML record) drives which subset of this list the
# optimizer sees.
ALL_PARAMS: tuple[str, ...] = (
    "drift_per_unit_evidence",
    "boundary",
    "non_decision_time",
    "starting_point",
    "drift_bias",
)
DEFAULT_FIXED: dict[str, float] = {
    "starting_point": 0.5,
    "drift_bias": 0.0,
    "lapse": 0.0,
}


def _resolve_params(
    free_values: dict[str, float],
    fixed_values: dict[str, float] | None = None,
) -> dict[str, float]:
    """Merge free, variant-fixed, and family-default parameters into a
    full parameter dict that the forward functions can consume."""
    merged = dict(DEFAULT_FIXED)
    if fixed_values:
        merged.update(fixed_values)
    merged.update(free_values)
    return merged


def predict_p_right(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    k = params["drift_per_unit_evidence"]
    a = params["boundary"]
    z = params.get("starting_point", 0.5)
    v0 = params.get("drift_bias", 0.0)
    v = k * xs + v0
    out = np.full_like(xs, z, dtype=float)
    nonzero = np.abs(v) > 1e-9
    if np.any(nonzero):
        v_nz = v[nonzero]
        num = 1.0 - np.exp(-np.clip(2.0 * v_nz * z * a, -700.0, 700.0))
        den = 1.0 - np.exp(-np.clip(2.0 * v_nz * a, -700.0, 700.0))
        # Guard near-zero denominators with the v→0 limit (z).
        safe = np.abs(den) > 1e-12
        ratio = np.full_like(v_nz, z)
        ratio[safe] = num[safe] / den[safe]
        out[nonzero] = ratio
    return np.clip(out, 0.0, 1.0)


def predict_mean_decision_time(
    params: dict[str, float], abs_xs: np.ndarray
) -> np.ndarray:
    """Marginal mean decision time using the unbiased EZ-DDM closed form
    with effective drift |k·|x| + v0|. Approximation note: starting-point
    bias does not enter; drift bias enters only through |v_eff|."""
    k = params["drift_per_unit_evidence"]
    a = params["boundary"]
    v0 = params.get("drift_bias", 0.0)
    abs_xs = np.asarray(abs_xs, dtype=float)
    v_eff = np.abs(k * abs_xs + v0)
    out = np.empty_like(v_eff)
    nonzero = v_eff > 1e-9
    if np.any(nonzero):
        out[nonzero] = (a / (2.0 * v_eff[nonzero])) * np.tanh(
            np.clip(v_eff[nonzero] * a, -50.0, 50.0)
        )
    out[~nonzero] = (a * a) / 4.0
    return out


def predict_mean_rt(params: dict[str, float], abs_xs: np.ndarray) -> np.ndarray:
    return predict_mean_decision_time(params, abs_xs) + params["non_decision_time"]


def _forward_with_variant_defaults(
    params: dict[str, float], finding: Finding
) -> list[CurvePoint]:
    full = _resolve_params(dict(params))
    xs = np.array([p.x for p in finding.curve.points])
    if finding.curve.curve_type == "psychometric":
        ys = predict_p_right(full, xs)
    elif finding.curve.curve_type == "chronometric":
        ys = predict_mean_rt(full, np.abs(xs))
    else:
        raise ValueError(
            f"DDM forward only handles psychometric or chronometric curves; "
            f"got {finding.curve.curve_type!r}."
        )
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


# Registered as the same forward for all three variants — the family
# is the same, only the free-parameter set differs.
register_forward(VARIANT_VANILLA, _forward_with_variant_defaults)
register_forward(VARIANT_Z_BIAS, _forward_with_variant_defaults)
register_forward(VARIANT_V_BIAS, _forward_with_variant_defaults)


def forward(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    return _forward_with_variant_defaults(params, finding)


def _negative_log_likelihood(
    free_values: dict[str, float],
    fixed_values: dict[str, float],
    *,
    psy_xs: np.ndarray,
    psy_ns: np.ndarray,
    psy_ks: np.ndarray,
    chr_abs_xs: np.ndarray,
    chr_ys: np.ndarray,
    rt_sigma: float,
) -> float:
    full = _resolve_params(free_values, fixed_values)
    p = predict_p_right(full, psy_xs)
    p = np.clip(p, 1e-9, 1.0 - 1e-9)
    binom = -np.sum(psy_ks * np.log(p) + (psy_ns - psy_ks) * np.log(1.0 - p))
    rt_pred = predict_mean_rt(full, chr_abs_xs)
    rt = 0.5 * np.sum(((rt_pred - chr_ys) / rt_sigma) ** 2)
    return float(binom + rt)


def _bounds_for(param: str, *, x_range: float, min_rt: float) -> tuple[float, float]:
    if param == "drift_per_unit_evidence":
        return (1e-6, 100.0 / x_range)
    if param == "boundary":
        return (1e-3, 10.0)
    if param == "non_decision_time":
        return (0.0, max(min_rt, 1e-6))
    if param == "starting_point":
        return (0.05, 0.95)
    if param == "drift_bias":
        return (-100.0 / x_range, 100.0 / x_range)
    raise ValueError(f"No bounds defined for parameter {param!r}")


def _initial_for(param: str, *, x_range: float, min_rt: float) -> float:
    if param == "drift_per_unit_evidence":
        return 1.0 / x_range
    if param == "boundary":
        return 1.0
    if param == "non_decision_time":
        return 0.5 * max(min_rt, 1e-3)
    if param == "starting_point":
        return 0.5
    if param == "drift_bias":
        return 0.0
    raise ValueError(f"No initial value for parameter {param!r}")


def fit_variant(
    finding: Finding,
    *,
    free_parameters: list[str],
    fixed_parameters: dict[str, float] | None = None,
    chronometric: Finding | None = None,
) -> dict[str, Any]:
    """Generalized DDM fit: free a chosen subset of {k, a, t0, z, v0}
    and joint-optimize over a (psychometric, chronometric) pair."""
    if finding.curve.curve_type != "psychometric":
        raise ValueError(
            "DDM fit anchors on the psychometric finding; "
            f"got {finding.curve.curve_type!r}."
        )
    if chronometric is None:
        raise ValueError(
            "DDM fit requires a paired chronometric finding; none supplied."
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
    min_rt = float(chr_ys.min())

    bounds = [
        _bounds_for(p, x_range=x_range, min_rt=min_rt) for p in free_parameters
    ]
    x0 = np.array(
        [_initial_for(p, x_range=x_range, min_rt=min_rt) for p in free_parameters]
    )
    fixed_values = dict(fixed_parameters or {})

    def _objective(theta: np.ndarray) -> float:
        free_values = dict(zip(free_parameters, theta, strict=True))
        return _negative_log_likelihood(
            free_values,
            fixed_values,
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
    n_free = len(free_parameters)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)
    free_values = dict(zip(free_parameters, [float(v) for v in result.x], strict=True))
    full_params = _resolve_params(free_values, fixed_values)

    psy_pred = predict_p_right(full_params, psy_xs)
    predictions = [
        {"x": float(x), "n": int(n), "y": float(y)}
        for x, n, y in zip(psy_xs, psy_ns, psy_pred, strict=True)
    ]
    chr_pred = predict_mean_rt(full_params, chr_abs_xs)
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
        "parameters": free_values,
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


# Backward-compatible entry point matching the old name. Defaults to
# the vanilla variant's free-parameter list.
def fit(finding: Finding, *, chronometric: Finding | None = None) -> dict[str, Any]:
    return fit_variant(
        finding,
        free_parameters=[
            "drift_per_unit_evidence",
            "boundary",
            "non_decision_time",
        ],
        fixed_parameters={"starting_point": 0.5, "drift_bias": 0.0},
        chronometric=chronometric,
    )


# Aliases for the bias variants — used by cli dispatch.
def fit_z_bias(finding: Finding, *, chronometric: Finding | None = None) -> dict[str, Any]:
    return fit_variant(
        finding,
        free_parameters=[
            "drift_per_unit_evidence",
            "boundary",
            "non_decision_time",
            "starting_point",
        ],
        fixed_parameters={"drift_bias": 0.0},
        chronometric=chronometric,
    )


def fit_v_bias(finding: Finding, *, chronometric: Finding | None = None) -> dict[str, Any]:
    return fit_variant(
        finding,
        free_parameters=[
            "drift_per_unit_evidence",
            "boundary",
            "non_decision_time",
            "drift_bias",
        ],
        fixed_parameters={"starting_point": 0.5},
        chronometric=chronometric,
    )


# Backward-compat: the cli imports VARIANT_ID for the dispatch
VARIANT_ID = VARIANT_VANILLA
