"""Forward + fit for descriptive median-RT chronometric curves."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize

from behavtaskatlas.model_layer import register_forward
from behavtaskatlas.models import CurvePoint, Finding

VARIANT_HYPERBOLIC_ID = "model_variant.chronometric-hyperbolic-rt"
VARIANT_CONSTANT_ID = "model_variant.chronometric-constant-rt"
VARIANT_ID = VARIANT_HYPERBOLIC_ID
CHRONOMETRIC_SUMMARY_VARIANT_IDS = frozenset(
    {VARIANT_HYPERBOLIC_ID, VARIANT_CONSTANT_ID}
)
PARAM_ORDER = ("rt_floor", "rt_span", "half_saturation_strength")
CONSTANT_PARAM_ORDER = ("rt_level",)


def predict(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    strength = np.abs(xs.astype(float))
    rt_floor = max(float(params["rt_floor"]), 0.0)
    rt_span = max(float(params["rt_span"]), 0.0)
    half_strength = max(float(params["half_saturation_strength"]), 1e-9)
    return rt_floor + rt_span / (1.0 + strength / half_strength)


def predict_constant(params: dict[str, float], xs: np.ndarray) -> np.ndarray:
    rt_level = max(float(params["rt_level"]), 0.0)
    return np.full_like(xs, rt_level, dtype=float)


def forward(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    xs = np.array([p.x for p in finding.curve.points])
    ys = predict(params, xs)
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def forward_constant(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    xs = np.array([p.x for p in finding.curve.points])
    ys = predict_constant(params, xs)
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def _chronometric_arrays(
    finding: Finding,
    *,
    variant_label: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    if finding.curve.curve_type != "chronometric":
        raise ValueError(f"{variant_label} fits require a chronometric finding.")

    xs = np.array([p.x for p in finding.curve.points], dtype=float)
    ys = np.array([p.y for p in finding.curve.points], dtype=float)
    ns = np.array([p.n for p in finding.curve.points], dtype=float)
    n_points = len(xs)
    n_trials = int(ns.sum())
    if n_points == 0:
        raise ValueError("Chronometric RT fit requires at least one curve point.")
    if n_trials <= 0:
        raise ValueError("Chronometric RT fit requires at least one trial.")
    if np.any(ys < 0):
        raise ValueError("Chronometric RT fit requires non-negative RT values.")
    return xs, ys, ns, n_points, n_trials


def _summary_fit_quality(
    *,
    ys: np.ndarray,
    ns: np.ndarray,
    predictions: np.ndarray,
    n_points: int,
    n_trials: int,
    n_free: int,
) -> dict[str, float]:
    rt_sigma = max(float(np.std(ys)), 1e-3)
    weights = ns / max(float(np.mean(ns)), 1.0)
    residuals = predictions - ys
    log_likelihood = float(-0.5 * np.sum(weights * (residuals / rt_sigma) ** 2))
    return {
        "log_likelihood": log_likelihood,
        "aic": float(2 * n_free - 2 * log_likelihood),
        "bic": float(n_free * np.log(max(n_points, 1)) - 2 * log_likelihood),
        "n_trials": float(n_trials),
        "n_points": float(n_points),
        "n_free_params": float(n_free),
        "chronometric_max_residual_s": float(np.max(np.abs(residuals))),
        "rt_sigma_assumed_s": rt_sigma,
    }


def _negative_log_likelihood(
    theta: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    weights: np.ndarray,
    rt_sigma: float,
) -> float:
    params = dict(zip(PARAM_ORDER, theta, strict=True))
    pred = predict(params, xs)
    return float(0.5 * np.sum(weights * ((pred - ys) / rt_sigma) ** 2))


def fit(finding: Finding) -> dict[str, Any]:
    xs, ys, ns, n_points, n_trials = _chronometric_arrays(
        finding,
        variant_label="Chronometric hyperbolic RT",
    )

    strengths = np.abs(xs)
    positive_strengths = strengths[strengths > 0]
    max_strength = max(float(strengths.max()), 1e-6)
    max_rt = max(float(ys.max()), 1e-6)
    min_rt = max(float(ys.min()), 0.0)
    span0 = max(float(ys.max() - ys.min()), 1e-6)
    half0 = (
        float(np.median(positive_strengths))
        if positive_strengths.size
        else max_strength
    )
    rt_sigma = max(float(np.std(ys)), 1e-3)
    weights = ns / max(float(np.mean(ns)), 1.0)

    x0 = np.array([min_rt, span0, max(half0, 1e-6)])
    bounds = [
        (0.0, 2.0 * max_rt),
        (0.0, 3.0 * max_rt),
        (1e-6, 100.0 * max_strength),
    ]
    result = minimize(
        _negative_log_likelihood,
        x0,
        args=(xs, ys, weights, rt_sigma),
        method="L-BFGS-B",
        bounds=bounds,
    )

    log_likelihood = float(-result.fun)
    n_free = len(PARAM_ORDER)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_points, 1)) - 2 * log_likelihood)
    parameters = dict(zip(PARAM_ORDER, [float(v) for v in result.x], strict=True))
    predictions = [
        {"x": float(x), "n": int(n), "y": float(y)}
        for x, n, y in zip(xs, ns, predict(parameters, xs), strict=True)
    ]
    residuals = predict(parameters, xs) - ys
    quality = {
        "log_likelihood": log_likelihood,
        "aic": aic,
        "bic": bic,
        "n_trials": float(n_trials),
        "n_points": float(n_points),
        "n_free_params": float(n_free),
        "chronometric_max_residual_s": float(np.max(np.abs(residuals))),
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
                "loss": "weighted Gaussian summary chi-squared",
            },
            "duration_seconds": None,
        },
        "success": bool(result.success),
        "message": str(getattr(result, "message", "")),
    }


def fit_constant(finding: Finding) -> dict[str, Any]:
    xs, ys, ns, n_points, n_trials = _chronometric_arrays(
        finding,
        variant_label="Chronometric constant RT",
    )
    weights = ns / max(float(np.mean(ns)), 1.0)
    rt_level = float(np.average(ys, weights=weights))
    parameters = {"rt_level": max(rt_level, 0.0)}
    predicted = predict_constant(parameters, xs)
    n_free = len(CONSTANT_PARAM_ORDER)
    quality = _summary_fit_quality(
        ys=ys,
        ns=ns,
        predictions=predicted,
        n_points=n_points,
        n_trials=n_trials,
        n_free=n_free,
    )
    predictions = [
        {"x": float(x), "n": int(n), "y": float(y)}
        for x, n, y in zip(xs, ns, predicted, strict=True)
    ]
    return {
        "parameters": parameters,
        "quality": quality,
        "predictions": predictions,
        "fit_method": {
            "type": "manual",
            "options": {
                "estimator": "weighted mean median RT",
                "loss": "weighted Gaussian summary chi-squared",
            },
            "duration_seconds": None,
        },
        "success": True,
        "message": "closed-form weighted constant RT estimate",
    }


register_forward(VARIANT_HYPERBOLIC_ID, forward)
register_forward(VARIANT_CONSTANT_ID, forward_constant)
