"""Forward + fit for the click-rate accumulator family (Brunton 2013).

Each click contributes an impulse to a hidden integrator that may leak;
at the end of the click train the observer reports the sign of the
integrator (plus a decision criterion offset). The closed-form Gaussian
approximation:

  E[a(T) | clicks] = B · (Σ_right e^{−λ(T−t_R)} − Σ_left e^{−λ(T−t_L)})
  V[a(T) | clicks] = σ_a² · (Σ_right e^{−2λ(T−t_R)} + Σ_left e^{−2λ(T−t_L)})
                   + σ_s² · (1 − e^{−2λT}) / (2λ)            (for λ > 0)
                   + σ_s² · T                                  (for λ → 0)
  P(right) = λ_lapse / 2 + (1 − λ_lapse) · Φ((E − bias) / √V)

Free parameters declared by `model_variant.click-leaky-accumulator`:
input_gain (B), leak (λ), noise_input (σ_a), noise_accumulator (σ_s),
bias (b), lapse (λ_lapse).

Fits and forward both read the slice-level concatenated `trials.csv`
(produced by `clicks-aggregate`) and filter by subject_id. If that
ignored derived artifact is unavailable, forward evaluation falls back
to a tracked compact trial cache with the same click-timing fields. The
model audit therefore still catches harmonization drift in clean CI
checkouts.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

from behavtaskatlas.model_layer import register_forward
from behavtaskatlas.models import CurvePoint, Finding

VARIANT_LEAKY_ID = "model_variant.click-leaky-accumulator"
VARIANT_COUNT_LOGISTIC_ID = "model_variant.click-count-logistic"
VARIANT_CHOICE_RATE_NULL_ID = "model_variant.click-choice-rate-null"
VARIANT_ID = VARIANT_LEAKY_ID
CLICK_SUMMARY_VARIANT_IDS = frozenset(
    {
        VARIANT_LEAKY_ID,
        VARIANT_COUNT_LOGISTIC_ID,
        VARIANT_CHOICE_RATE_NULL_ID,
    }
)
PARAM_ORDER = (
    "input_gain",
    "leak",
    "noise_input",
    "noise_accumulator",
    "bias",
    "lapse",
)
COUNT_LOGISTIC_PARAM_ORDER = ("sensitivity", "bias", "lapse")
CHOICE_RATE_NULL_PARAM_ORDER = ("response_rate",)
SLICE_TRIALS_PATH = Path("derived/auditory_clicks/trials.csv")
COMPACT_CLICK_TRIALS_PATH = Path("model_inputs/auditory_clicks/trials_compact.npz")


def _load_clicks(
    trials_path: Path, subject_id: str | None
) -> dict[str, Any]:
    """Read trials.csv and parse click features. Cached separately
    from the lru_cache helper above (which is unused — kept for API
    shape) because the data is per-subject and used only at fit time.
    """
    rows: list[dict[str, str]] = []
    with trials_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if subject_id is not None and row.get("subject_id") != subject_id:
                continue
            choice = (row.get("choice") or "").strip()
            if choice not in {"left", "right"}:
                continue
            rows.append(row)
    n = len(rows)
    stim_values = np.empty(n, dtype=float)
    choices = np.empty(n, dtype=np.int8)
    durations = np.empty(n, dtype=float)
    right_times: list[np.ndarray] = []
    left_times: list[np.ndarray] = []
    for i, row in enumerate(rows):
        try:
            stim_values[i] = float(row.get("stimulus_value", "nan"))
        except ValueError:
            stim_values[i] = float("nan")
        choices[i] = 1 if (row.get("choice") or "").strip() == "right" else 0
        tv = json.loads(row.get("task_variables_json") or "{}")
        rt = np.asarray(tv.get("right_click_times", []), dtype=float)
        lt = np.asarray(tv.get("left_click_times", []), dtype=float)
        if not np.isfinite(stim_values[i]):
            stim_values[i] = float(rt.size - lt.size)
        right_times.append(rt)
        left_times.append(lt)
        T = float(tv.get("stimulus_duration") or 0.0)
        if T <= 0:
            t_max = 0.0
            if rt.size:
                t_max = max(t_max, float(rt.max()))
            if lt.size:
                t_max = max(t_max, float(lt.max()))
            T = max(t_max, 1e-3)
        durations[i] = T
    return {
        "stimulus_values": stim_values,
        "choices": choices,
        "durations": durations,
        "right_times": right_times,
        "left_times": left_times,
        "n_trials": n,
    }


def _load_compact_clicks(
    compact_path: Path, subject_id: str | None
) -> dict[str, Any]:
    with np.load(compact_path, allow_pickle=False) as payload:
        subject_labels = [str(value) for value in payload["subject_labels"]]
        subject_codes = payload["subject_code"].astype(np.int64, copy=False)
        if subject_id is None:
            row_indices = np.arange(subject_codes.size)
        else:
            normalized_subject_id = subject_id.upper()
            label_by_id = {label.upper(): i for i, label in enumerate(subject_labels)}
            if normalized_subject_id not in label_by_id:
                row_indices = np.array([], dtype=np.int64)
            else:
                code = label_by_id[normalized_subject_id]
                row_indices = np.flatnonzero(subject_codes == code)

        stim_values = payload["stimulus_values"][row_indices].astype(float, copy=True)
        choices = payload["choices"][row_indices].astype(np.int8, copy=True)
        durations = payload["durations"][row_indices].astype(float, copy=True)
        right_offsets = payload["right_offsets"].astype(np.int64, copy=False)
        left_offsets = payload["left_offsets"].astype(np.int64, copy=False)
        right_times_all = payload["right_times"].astype(float, copy=False)
        left_times_all = payload["left_times"].astype(float, copy=False)

        right_times = [
            right_times_all[right_offsets[i] : right_offsets[i + 1]].copy()
            for i in row_indices
        ]
        left_times = [
            left_times_all[left_offsets[i] : left_offsets[i + 1]].copy()
            for i in row_indices
        ]

    return {
        "stimulus_values": stim_values,
        "choices": choices,
        "durations": durations,
        "right_times": right_times,
        "left_times": left_times,
        "n_trials": int(row_indices.size),
    }


def _per_trial_E_V(
    params: dict[str, float], data: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    B = params["input_gain"]
    leak = params["leak"]
    sa2 = params["noise_input"] ** 2
    ss2 = params["noise_accumulator"] ** 2
    durations = data["durations"]
    n = data["n_trials"]
    E = np.zeros(n, dtype=float)
    V = np.zeros(n, dtype=float)
    for i in range(n):
        T = durations[i]
        rt = data["right_times"][i]
        lt = data["left_times"][i]
        if leak > 1e-12:
            wR = np.exp(-np.clip(leak * (T - rt), -50.0, 50.0)) if rt.size else np.zeros(0)
            wL = np.exp(-np.clip(leak * (T - lt), -50.0, 50.0)) if lt.size else np.zeros(0)
            wR2 = np.exp(-np.clip(2.0 * leak * (T - rt), -50.0, 50.0)) if rt.size else np.zeros(0)
            wL2 = np.exp(-np.clip(2.0 * leak * (T - lt), -50.0, 50.0)) if lt.size else np.zeros(0)
            diffusion_var = ss2 * (1.0 - np.exp(-min(2.0 * leak * T, 50.0))) / (2.0 * leak)
        else:
            wR = np.ones_like(rt)
            wL = np.ones_like(lt)
            wR2 = np.ones_like(rt)
            wL2 = np.ones_like(lt)
            diffusion_var = ss2 * T
        E[i] = B * (wR.sum() - wL.sum())
        V[i] = sa2 * (wR2.sum() + wL2.sum()) + diffusion_var
    return E, V


def predict_p_right_per_trial(
    params: dict[str, float], data: dict[str, Any]
) -> np.ndarray:
    E, V = _per_trial_E_V(params, data)
    sigma = np.sqrt(np.maximum(V, 1e-12))
    z = (E - params["bias"]) / sigma
    base = norm.cdf(z)
    lapse = params["lapse"]
    return lapse / 2.0 + (1.0 - lapse) * base


def _logistic_cdf(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -700.0, 700.0)))


def predict_count_logistic(
    params: dict[str, float], signed_click_difference: np.ndarray
) -> np.ndarray:
    sensitivity = float(params["sensitivity"])
    bias = float(params["bias"])
    lapse = float(np.clip(params["lapse"], 0.0, 0.5))
    if sensitivity <= 0:
        return np.full_like(signed_click_difference, 0.5, dtype=float)
    base = _logistic_cdf(sensitivity * (signed_click_difference - bias))
    return lapse / 2.0 + (1.0 - lapse) * base


def predict_choice_rate_null(
    params: dict[str, float], xs: np.ndarray
) -> np.ndarray:
    response_rate = float(np.clip(params["response_rate"], 1e-9, 1.0 - 1e-9))
    return np.full_like(xs, response_rate, dtype=float)


def _aggregate_to_curve(
    finding_xs: np.ndarray,
    stim_values: np.ndarray,
    p_per_trial: np.ndarray,
    counts: np.ndarray,
) -> list[CurvePoint]:
    points: list[CurvePoint] = []
    for x in finding_xs:
        mask = stim_values == x
        n = int(mask.sum())
        if n == 0:
            points.append(CurvePoint(x=float(x), n=0, y=0.5))
            continue
        y_pred = float(np.mean(p_per_trial[mask]))
        points.append(CurvePoint(x=float(x), n=n, y=y_pred))
    return points


_TRIAL_CACHE: dict[tuple[str, str | None], dict[str, Any]] = {}


def _load_cached(subject_id: str | None) -> dict[str, Any] | None:
    if SLICE_TRIALS_PATH.exists():
        source_path = SLICE_TRIALS_PATH
        loader = _load_clicks
    elif COMPACT_CLICK_TRIALS_PATH.exists():
        source_path = COMPACT_CLICK_TRIALS_PATH
        loader = _load_compact_clicks
    else:
        return None
    key = (str(source_path), subject_id)
    if key in _TRIAL_CACHE:
        return _TRIAL_CACHE[key]
    data = loader(source_path, subject_id)
    _TRIAL_CACHE[key] = data
    return data


def forward(params: dict[str, float], finding: Finding) -> list[CurvePoint]:
    subject_id = finding.stratification.subject_id
    data = _load_cached(subject_id)
    if data is None or data["n_trials"] == 0:
        return [CurvePoint(x=p.x, n=p.n, y=0.5) for p in finding.curve.points]
    p_trial = predict_p_right_per_trial(params, data)
    finding_xs = np.array([p.x for p in finding.curve.points])
    return _aggregate_to_curve(
        finding_xs, data["stimulus_values"], p_trial, np.array([p.n for p in finding.curve.points])
    )


def forward_count_logistic(
    params: dict[str, float], finding: Finding
) -> list[CurvePoint]:
    subject_id = finding.stratification.subject_id
    data = _load_cached(subject_id)
    if data is None or data["n_trials"] == 0:
        return [CurvePoint(x=p.x, n=p.n, y=0.5) for p in finding.curve.points]
    signed_click_difference = np.asarray(data["stimulus_values"], dtype=float)
    mask = np.isfinite(signed_click_difference)
    if not np.any(mask):
        return [CurvePoint(x=p.x, n=p.n, y=0.5) for p in finding.curve.points]
    p_trial = predict_count_logistic(params, signed_click_difference[mask])
    finding_xs = np.array([p.x for p in finding.curve.points])
    return _aggregate_to_curve(
        finding_xs,
        signed_click_difference[mask],
        p_trial,
        np.array([p.n for p in finding.curve.points]),
    )


def forward_choice_rate_null(
    params: dict[str, float], finding: Finding
) -> list[CurvePoint]:
    xs = np.array([p.x for p in finding.curve.points])
    ys = predict_choice_rate_null(params, xs)
    return [
        CurvePoint(x=p.x, n=p.n, y=float(y))
        for p, y in zip(finding.curve.points, ys, strict=True)
    ]


def fit(finding: Finding) -> dict[str, Any]:
    subject_id = finding.stratification.subject_id
    if subject_id is None:
        raise ValueError(
            "Click-rate fit currently anchors on per-subject psychometric "
            "findings; pooled fits not implemented."
        )
    data = _load_cached(subject_id)
    if data is None or data["n_trials"] == 0:
        raise ValueError(
            f"No click trials found for subject_id={subject_id!r} at "
            f"{SLICE_TRIALS_PATH}; run clicks-aggregate-trials first."
        )

    choices = data["choices"].astype(float)

    def _objective(theta: np.ndarray) -> float:
        params = dict(zip(PARAM_ORDER, theta, strict=True))
        if params["lapse"] < 0 or params["lapse"] > 0.5:
            return 1e9
        if params["input_gain"] <= 0 or params["leak"] < 0:
            return 1e9
        if params["noise_input"] < 0 or params["noise_accumulator"] < 0:
            return 1e9
        p = predict_p_right_per_trial(params, data)
        p = np.clip(p, 1e-9, 1.0 - 1e-9)
        return float(-np.sum(choices * np.log(p) + (1.0 - choices) * np.log(1.0 - p)))

    # Heuristic initial values + bounds. Click data: stimulus_value
    # spans roughly ±25 (right minus left clicks); B around 1 puts E
    # in the σ_a*sqrt(N) range.
    x0 = np.array([1.0, 0.5, 0.5, 1.0, 0.0, 0.05])
    bounds = [
        (1e-3, 100.0),  # input_gain
        (0.0, 50.0),    # leak (1/s)
        (0.0, 10.0),    # noise_input
        (0.0, 50.0),    # noise_accumulator
        (-50.0, 50.0),  # bias
        (0.0, 0.5),     # lapse
    ]
    result = minimize(
        _objective,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 500},
    )
    parameters = dict(zip(PARAM_ORDER, [float(v) for v in result.x], strict=True))
    log_likelihood = float(-result.fun)
    n_trials = int(data["n_trials"])
    n_free = len(PARAM_ORDER)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)

    p_per_trial = predict_p_right_per_trial(parameters, data)
    finding_xs = np.array([p.x for p in finding.curve.points])
    curve = _aggregate_to_curve(
        finding_xs,
        data["stimulus_values"],
        p_per_trial,
        np.array([p.n for p in finding.curve.points]),
    )
    predictions = [{"x": float(p.x), "n": int(p.n), "y": float(p.y)} for p in curve]
    quality = {
        "log_likelihood": log_likelihood,
        "aic": aic,
        "bic": bic,
        "n_trials": float(n_trials),
        "n_free_params": float(n_free),
    }
    return {
        "parameters": parameters,
        "quality": quality,
        "predictions": predictions,
        "fit_method": {
            "type": "scipy.optimize.minimize",
            "options": {
                "method": "L-BFGS-B",
                "loss": "per-trial Bernoulli NLL with closed-form Gaussian variance",
            },
            "duration_seconds": None,
        },
        "success": bool(result.success),
        "message": str(getattr(result, "message", "")),
    }


def fit_count_logistic(finding: Finding) -> dict[str, Any]:
    subject_id = finding.stratification.subject_id
    if subject_id is None:
        raise ValueError(
            "Click-count logistic fits currently anchor on per-subject "
            "psychometric findings."
        )
    data = _load_cached(subject_id)
    if data is None or data["n_trials"] == 0:
        raise ValueError(
            f"No click trials found for subject_id={subject_id!r} at "
            f"{SLICE_TRIALS_PATH}; run clicks-aggregate-trials first."
        )

    signed_click_difference = np.asarray(data["stimulus_values"], dtype=float)
    mask = np.isfinite(signed_click_difference)
    if not np.any(mask):
        raise ValueError(
            f"No finite signed click-count differences found for {subject_id!r}."
        )
    xs = signed_click_difference[mask]
    choices = data["choices"].astype(float)[mask]

    def _objective(theta: np.ndarray) -> float:
        params = dict(zip(COUNT_LOGISTIC_PARAM_ORDER, theta, strict=True))
        if params["sensitivity"] <= 0:
            return 1e9
        if params["lapse"] < 0 or params["lapse"] > 0.5:
            return 1e9
        p = predict_count_logistic(params, xs)
        p = np.clip(p, 1e-9, 1.0 - 1e-9)
        return float(-np.sum(choices * np.log(p) + (1.0 - choices) * np.log(1.0 - p)))

    x_min = float(xs.min())
    x_max = float(xs.max())
    x_range = max(x_max - x_min, 1e-6)
    x0 = np.array([4.0 / x_range, 0.0, 0.05])
    bounds = [
        (1e-6, 100.0 / x_range),  # sensitivity per click
        (x_min - 1.0, x_max + 1.0),  # bias in right-minus-left clicks
        (0.0, 0.5),  # lapse
    ]
    result = minimize(
        _objective,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 500},
    )
    parameters = dict(
        zip(COUNT_LOGISTIC_PARAM_ORDER, [float(v) for v in result.x], strict=True)
    )
    log_likelihood = float(-result.fun)
    n_trials = int(xs.size)
    n_free = len(COUNT_LOGISTIC_PARAM_ORDER)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)
    p_per_trial = predict_count_logistic(parameters, xs)
    finding_xs = np.array([p.x for p in finding.curve.points])
    curve = _aggregate_to_curve(
        finding_xs,
        xs,
        p_per_trial,
        np.array([p.n for p in finding.curve.points]),
    )
    predictions = [{"x": float(p.x), "n": int(p.n), "y": float(p.y)} for p in curve]
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
            "type": "scipy.optimize.minimize",
            "options": {
                "method": "L-BFGS-B",
                "loss": "per-trial Bernoulli NLL over signed click-count difference",
            },
            "duration_seconds": None,
        },
        "success": bool(result.success),
        "message": str(getattr(result, "message", "")),
    }


def fit_choice_rate_null(finding: Finding) -> dict[str, Any]:
    subject_id = finding.stratification.subject_id
    if subject_id is None:
        raise ValueError(
            "Click choice-rate null fits currently anchor on per-subject "
            "psychometric findings."
        )
    data = _load_cached(subject_id)
    if data is None or data["n_trials"] == 0:
        raise ValueError(
            f"No click trials found for subject_id={subject_id!r} at "
            f"{SLICE_TRIALS_PATH}; run clicks-aggregate-trials first."
        )

    choices = data["choices"].astype(float)
    n_trials = int(choices.size)
    if n_trials <= 0:
        raise ValueError("Click choice-rate null requires at least one trial.")
    response_rate = float(np.clip(choices.mean(), 1e-9, 1.0 - 1e-9))
    p = np.full_like(choices, response_rate, dtype=float)
    log_likelihood = float(
        np.sum(choices * np.log(p) + (1.0 - choices) * np.log(1.0 - p))
    )
    n_free = len(CHOICE_RATE_NULL_PARAM_ORDER)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * np.log(max(n_trials, 1)) - 2 * log_likelihood)
    xs = np.array([p.x for p in finding.curve.points])
    predictions = [
        {"x": float(x), "n": int(point.n), "y": response_rate}
        for x, point in zip(xs, finding.curve.points, strict=True)
    ]
    return {
        "parameters": {"response_rate": response_rate},
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
            "options": {"estimator": "per-subject Bernoulli maximum likelihood"},
            "duration_seconds": None,
        },
        "success": True,
        "message": "closed-form per-subject Bernoulli MLE",
    }


register_forward(VARIANT_LEAKY_ID, forward)
register_forward(VARIANT_COUNT_LOGISTIC_ID, forward_count_logistic)
register_forward(VARIANT_CHOICE_RATE_NULL_ID, forward_choice_rate_null)
