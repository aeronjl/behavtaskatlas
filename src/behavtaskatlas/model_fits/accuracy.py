"""Forward + fit for chance-floor accuracy-by-strength curves."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize

from behavtaskatlas.model_layer import register_forward
from behavtaskatlas.models import CurvePoint, Finding

VARIANT_LOGISTIC_ID = "model_variant.chance-floor-accuracy-logistic"
VARIANT_RATE_NULL_ID = "model_variant.accuracy-rate-null"
VARIANT_ID = VARIANT_LOGISTIC_ID
ACCURACY_SUMMARY_VARIANT_IDS = frozenset(
    {VARIANT_LOGISTIC_ID, VARIANT_RATE_NULL_ID}
)
PARAM_ORDER = ("threshold_strength", "slope_log2", "lapse")
RATE_NULL_PARAM_ORDER = ("accuracy_rate",)
CHANCE_FLOOR = 0.5


def _logistic_cdf(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -700.0, 700.0)))


def predict(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    threshold = max(float(params["threshold_strength"]), 1e-12)
    slope = max(float(params["slope_log2"]), 1e-6)
    lapse = float(np.clip(params["lapse"], 0.0, 0.49))
    safe_xs = np.clip(xs.astype(float), 1e-12, None)
    z = (np.log2(safe_xs) - np.log2(threshold)) / slope
    return CHANCE_FLOOR + (1.0 - CHANCE_FLOOR - lapse) * _logistic_cdf(z)


def predict_rate_null(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    accuracy_rate = float(np.clip(params["accuracy_rate"], CHANCE_FLOOR, 1.0 - 1e-9))
    return np.full_like(xs, accuracy_rate, dtype=float)


def forward(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    xs = np.array([p.x for p in finding.curve.points])
    ys = predict(params, xs)
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def forward_rate_null(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    xs = np.array([p.x for p in finding.curve.points])
    ys = predict_rate_null(params, xs)
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def _accuracy_arrays(
    finding: Finding,
    *,
    variant_label: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    if finding.curve.curve_type != "accuracy_by_strength":
        raise ValueError(f"{variant_label} fits require an accuracy_by_strength finding.")

    xs = np.array([p.x for p in finding.curve.points], dtype=float)
    if np.any(xs <= 0):
        raise ValueError("Accuracy strength fits require positive x values.")
    ns = np.array([p.n for p in finding.curve.points], dtype=float)
    ks = np.array(
        [int(round(p.y * p.n)) for p in finding.curve.points], dtype=float
    )
    n_trials = int(ns.sum())
    if n_trials <= 0:
        raise ValueError("Accuracy strength fit requires at least one trial.")
    return xs, ns, ks, n_trials


def _negative_log_likelihood(
    theta: np.ndarray, xs: np.ndarray, ns: np.ndarray, ks: np.ndarray
) -> float:
    params = dict(zip(PARAM_ORDER, theta, strict=True))
    p = np.clip(predict(params, xs), 1e-9, 1.0 - 1e-9)
    return float(-np.sum(ks * np.log(p) + (ns - ks) * np.log(1.0 - p)))


def fit(finding: Finding) -> dict[str, Any]:
    xs, ns, ks, n_trials = _accuracy_arrays(
        finding,
        variant_label="Chance-floor accuracy logistic",
    )

    log_xs = np.log2(xs)
    log_range = max(float(log_xs.max() - log_xs.min()), 1e-6)
    x0 = np.array(
        [
            float(np.median(xs)),
            max(log_range / 4.0, 1e-3),
            0.01,
        ]
    )
    bounds = [
        (float(xs.min()), float(xs.max())),
        (1e-3, 10.0 * log_range),
        (0.0, 0.49),
    ]
    result = minimize(
        _negative_log_likelihood,
        x0,
        args=(xs, ns, ks),
        method="L-BFGS-B",
        bounds=bounds,
    )
    log_likelihood = float(-result.fun)
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


def fit_rate_null(finding: Finding) -> dict[str, Any]:
    xs, ns, ks, n_trials = _accuracy_arrays(
        finding,
        variant_label="Accuracy rate null",
    )
    accuracy_rate = float(np.clip(ks.sum() / ns.sum(), CHANCE_FLOOR, 1.0 - 1e-9))
    predicted = predict_rate_null({"accuracy_rate": accuracy_rate}, xs)
    p = np.clip(predicted, 1e-9, 1.0 - 1e-9)
    log_likelihood = float(
        np.sum(ks * np.log(p) + (ns - ks) * np.log(1.0 - p))
    )
    n_free = len(RATE_NULL_PARAM_ORDER)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)
    predictions = [
        {"x": float(x), "n": int(n), "y": float(y)}
        for x, n, y in zip(xs, ns, predicted, strict=True)
    ]
    return {
        "parameters": {"accuracy_rate": accuracy_rate},
        "quality": {
            "log_likelihood": log_likelihood,
            "aic": aic,
            "bic": bic,
            "n_trials": float(n_trials),
            "n_free_params": float(n_free),
        },
        "predictions": predictions,
        "fit_method": {
            "type": "manual",
            "options": {
                "estimator": "binomial maximum likelihood",
                "chance_floor": CHANCE_FLOOR,
            },
            "duration_seconds": None,
        },
        "success": True,
        "message": "closed-form strength-invariant accuracy MLE",
    }


register_forward(VARIANT_LOGISTIC_ID, forward)
register_forward(VARIANT_RATE_NULL_ID, forward_rate_null)
