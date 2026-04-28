"""Forward + fit for the 2AFC equal-variance Gaussian SDT variant.

  y = Φ(d′ · x − c)

with Φ the standard normal CDF, d′ interpreted as a per-unit-stimulus
sensitivity slope and c the criterion. Fits maximize the binomial
likelihood of (x_i, n_i, k_i) under this probit psychometric.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

from behavtaskatlas.model_layer import register_forward
from behavtaskatlas.models import CurvePoint, Finding

VARIANT_ID = "model_variant.sdt-2afc"
PARAM_ORDER = ("d_prime", "criterion")


def predict(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    d_prime = params["d_prime"]
    c = params["criterion"]
    return norm.cdf(d_prime * xs - c)


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
    xs = np.array([p.x for p in finding.curve.points])
    ns = np.array([p.n for p in finding.curve.points])
    ks = np.array(
        [int(round(p.y * p.n)) for p in finding.curve.points], dtype=float
    )
    x_range = max(float(xs.max() - xs.min()), 1e-6)
    # Heuristic initial guesses: d′ ~ 4 / range so that the curve spans
    # roughly the central transition window; criterion at 0.
    x0 = np.array([4.0 / x_range, 0.0])
    bounds = [(1e-6, 100.0 / x_range), (-50.0, 50.0)]
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
