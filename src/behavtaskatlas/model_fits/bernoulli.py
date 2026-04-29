"""Forward + fit for Bernoulli condition-rate baselines."""

from __future__ import annotations

from typing import Any

import numpy as np

from behavtaskatlas.model_layer import register_forward
from behavtaskatlas.models import CurvePoint, Finding

VARIANT_RATE_ID = "model_variant.bernoulli-condition-rate"
VARIANT_SATURATED_ID = "model_variant.bernoulli-condition-saturated"
VARIANT_ID = VARIANT_RATE_ID
CONDITION_RATE_VARIANT_IDS = frozenset({VARIANT_RATE_ID, VARIANT_SATURATED_ID})
PARAM_ORDER = ("response_rate",)


def predict(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    p = float(np.clip(params["response_rate"], 1e-9, 1.0 - 1e-9))
    return np.full_like(xs, p, dtype=float)


def _condition_param_name(x: float) -> str:
    if float(x).is_integer():
        return f"response_rate_x{int(x)}"
    token = f"{float(x):.10g}".replace("-", "neg").replace(".", "p")
    return f"response_rate_x{token}"


def predict_saturated(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    values: list[float] = []
    fallback = float(np.clip(params.get("response_rate", 0.5), 1e-9, 1.0 - 1e-9))
    for x in xs.astype(float):
        value = np.clip(
            params.get(_condition_param_name(x), fallback),
            1e-9,
            1.0 - 1e-9,
        )
        values.append(float(value))
    return np.asarray(values, dtype=float)


def forward(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    xs = np.array([p.x for p in finding.curve.points])
    ys = predict(params, xs)
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def forward_saturated(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    xs = np.array([p.x for p in finding.curve.points])
    ys = predict_saturated(params, xs)
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def _condition_rate_arrays(
    finding: Finding,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    if finding.curve.curve_type != "hit_rate_by_condition":
        raise ValueError(
            "Bernoulli condition-rate fits require a hit_rate_by_condition finding."
        )

    xs = np.array([p.x for p in finding.curve.points], dtype=float)
    ns = np.array([p.n for p in finding.curve.points], dtype=float)
    ks = np.array(
        [int(round(p.y * p.n)) for p in finding.curve.points], dtype=float
    )
    n_trials = int(ns.sum())
    if n_trials <= 0:
        raise ValueError("Bernoulli condition-rate fit requires at least one trial.")
    if np.any(ns <= 0):
        raise ValueError("Bernoulli condition-rate fit requires positive counts.")
    return xs, ns, ks, n_trials


def fit(finding: Finding) -> dict[str, Any]:
    xs, ns, ks, n_trials = _condition_rate_arrays(finding)

    response_rate = float(np.clip(ks.sum() / ns.sum(), 1e-9, 1.0 - 1e-9))
    p = predict({"response_rate": response_rate}, xs)
    log_likelihood = float(
        np.sum(ks * np.log(p) + (ns - ks) * np.log(1.0 - p))
    )
    n_free = len(PARAM_ORDER)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)
    quality = {
        "log_likelihood": log_likelihood,
        "aic": aic,
        "bic": bic,
        "n_trials": float(n_trials),
        "n_free_params": float(n_free),
    }
    predictions = [
        {"x": float(x), "n": int(n), "y": float(y)}
        for x, n, y in zip(xs, ns, p, strict=True)
    ]
    return {
        "parameters": {"response_rate": response_rate},
        "quality": quality,
        "predictions": predictions,
        "fit_method": {
            "type": "manual",
            "options": {"estimator": "binomial maximum likelihood"},
            "duration_seconds": None,
        },
        "success": True,
        "message": "closed-form binomial MLE",
    }


def fit_saturated(finding: Finding) -> dict[str, Any]:
    xs, ns, ks, n_trials = _condition_rate_arrays(finding)

    rates = np.clip(ks / ns, 1e-9, 1.0 - 1e-9)
    parameters = {
        _condition_param_name(float(x)): float(rate)
        for x, rate in zip(xs, rates, strict=True)
    }
    p = predict_saturated(parameters, xs)
    log_likelihood = float(
        np.sum(ks * np.log(p) + (ns - ks) * np.log(1.0 - p))
    )
    n_free = int(len(xs))
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)
    predictions = [
        {"x": float(x), "n": int(n), "y": float(y)}
        for x, n, y in zip(xs, ns, p, strict=True)
    ]
    return {
        "parameters": parameters,
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
            "options": {"estimator": "per-condition binomial maximum likelihood"},
            "duration_seconds": None,
        },
        "success": True,
        "message": "closed-form per-condition Bernoulli MLE",
    }


register_forward(VARIANT_RATE_ID, forward)
register_forward(VARIANT_SATURATED_ID, forward_saturated)
