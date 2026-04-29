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
(produced by `clicks-aggregate`) and filter by subject_id. Forward at
audit time reproduces the predictions if the trial table is unchanged;
the model audit therefore catches any harmonization drift.
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

VARIANT_ID = "model_variant.click-leaky-accumulator"
PARAM_ORDER = (
    "input_gain",
    "leak",
    "noise_input",
    "noise_accumulator",
    "bias",
    "lapse",
)
SLICE_TRIALS_PATH = Path("derived/auditory_clicks/trials.csv")


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
        choices[i] = 1 if row.get("choice") == "right" else 0
        tv = json.loads(row.get("task_variables_json") or "{}")
        rt = np.asarray(tv.get("right_click_times", []), dtype=float)
        lt = np.asarray(tv.get("left_click_times", []), dtype=float)
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
    key = (str(SLICE_TRIALS_PATH), subject_id)
    if key in _TRIAL_CACHE:
        return _TRIAL_CACHE[key]
    if not SLICE_TRIALS_PATH.exists():
        return None
    data = _load_clicks(SLICE_TRIALS_PATH, subject_id)
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


register_forward(VARIANT_ID, forward)
