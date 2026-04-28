"""Forward + fit for the 4-parameter logistic psychometric.

  y = γ + (1 − γ − λ) · σ((x − μ) / σ_slope)

with σ(z) = 1 / (1 + exp(−z)). Fits maximize the binomial likelihood of
the observed (x_i, n_i, k_i) where k_i = round(p_right_i · n_i).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize

from behavtaskatlas.model_layer import register_forward
from behavtaskatlas.models import CurvePoint, Finding

VARIANT_ID = "model_variant.logistic-4param"
PARAM_ORDER = ("bias", "slope", "lower_lapse", "upper_lapse")


def _logistic_cdf(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -700.0, 700.0)))


def predict(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    mu = params["bias"]
    sigma = params["slope"]
    gamma = params["lower_lapse"]
    lam = params["upper_lapse"]
    if sigma <= 0:
        return np.full_like(xs, 0.5, dtype=float)
    return gamma + (1.0 - gamma - lam) * _logistic_cdf((xs - mu) / sigma)


def forward(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    xs = np.array([p.x for p in finding.curve.points])
    ys = predict(params, xs)
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def _negative_log_likelihood(
    theta: np.ndarray, xs: np.ndarray, ns: np.ndarray, ks: np.ndarray
) -> float:
    params = dict(zip(PARAM_ORDER, theta, strict=True))
    p = predict(params, xs)
    p = np.clip(p, 1e-9, 1.0 - 1e-9)
    return float(-np.sum(ks * np.log(p) + (ns - ks) * np.log(1.0 - p)))


def fit(finding: Finding) -> dict[str, Any]:
    """Run the logistic fit; return parameters + quality dict.

    Quality keys: log_likelihood, aic, bic, n_trials, n_free_params.
    Uses scipy.optimize.minimize (L-BFGS-B) with bounds on each
    parameter and a deterministic initial guess derived from the
    stimulus range.
    """
    xs = np.array([p.x for p in finding.curve.points])
    ns = np.array([p.n for p in finding.curve.points])
    ks = np.array(
        [int(round(p.y * p.n)) for p in finding.curve.points], dtype=float
    )
    x_range = max(float(xs.max() - xs.min()), 1e-6)
    x0 = np.array([0.0, x_range / 4.0, 0.05, 0.05])
    bounds = [
        (float(xs.min()), float(xs.max())),
        (1e-6, 10.0 * x_range),
        (0.0, 0.5),
        (0.0, 0.5),
    ]
    result = minimize(
        _negative_log_likelihood,
        x0,
        args=(xs, ns, ks),
        method="L-BFGS-B",
        bounds=bounds,
    )
    log_likelihood = float(-result.fun)
    n_trials = int(ns.sum())
    n_free = len(PARAM_ORDER)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)
    parameters = dict(zip(PARAM_ORDER, [float(v) for v in result.x], strict=True))
    quality = {
        "log_likelihood": log_likelihood,
        "aic": aic,
        "bic": bic,
        "n_trials": float(n_trials),
        "n_free_params": float(n_free),
    }
    predictions = [
        {"x": float(x), "n": int(n), "y": float(y)}
        for x, n, y in zip(xs, ns, predict(parameters, xs), strict=True)
    ]
    return {
        "parameters": parameters,
        "quality": quality,
        "predictions": predictions,
        "fit_method": {
            "type": "scipy.optimize.minimize",
            "options": {"method": "L-BFGS-B", "bounds": "see code"},
            "duration_seconds": None,
        },
        "success": bool(result.success),
        "message": str(getattr(result, "message", "")),
    }


register_forward(VARIANT_ID, forward)
