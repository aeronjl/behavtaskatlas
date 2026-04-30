"""Build the compact Brunton click-trial cache used by model audits."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_TRIALS_PATH = Path("derived/auditory_clicks/trials.csv")
DEFAULT_OUTPUT_PATH = Path("model_inputs/auditory_clicks/trials_compact.npz")


def _click_times(task_variables_json: str) -> tuple[np.ndarray, np.ndarray, float]:
    task_variables = json.loads(task_variables_json or "{}")
    right_times = np.asarray(task_variables.get("right_click_times", []), dtype=float)
    left_times = np.asarray(task_variables.get("left_click_times", []), dtype=float)
    duration = float(task_variables.get("stimulus_duration") or 0.0)
    if duration <= 0:
        t_max = 0.0
        if right_times.size:
            t_max = max(t_max, float(right_times.max()))
        if left_times.size:
            t_max = max(t_max, float(left_times.max()))
        duration = max(t_max, 1e-3)
    return right_times, left_times, duration


def build_compact_click_trials(trials_path: Path, output_path: Path) -> dict[str, Any]:
    subject_labels: list[str] = []
    subject_code_by_label: dict[str, int] = {}
    subject_codes: list[int] = []
    stimulus_values: list[float] = []
    choices: list[int] = []
    durations: list[float] = []
    right_offsets: list[int] = [0]
    left_offsets: list[int] = [0]
    right_times_all: list[float] = []
    left_times_all: list[float] = []

    with trials_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            choice = (row.get("choice") or "").strip()
            if choice not in {"left", "right"}:
                continue
            subject_id = (row.get("subject_id") or "").strip()
            if subject_id not in subject_code_by_label:
                subject_code_by_label[subject_id] = len(subject_labels)
                subject_labels.append(subject_id)
            right_times, left_times, duration = _click_times(
                row.get("task_variables_json") or "{}"
            )
            try:
                stimulus_value = float(row.get("stimulus_value", "nan"))
            except ValueError:
                stimulus_value = float("nan")
            if not np.isfinite(stimulus_value):
                stimulus_value = float(right_times.size - left_times.size)

            subject_codes.append(subject_code_by_label[subject_id])
            stimulus_values.append(stimulus_value)
            choices.append(1 if choice == "right" else 0)
            durations.append(duration)
            right_times_all.extend(float(value) for value in right_times)
            left_times_all.extend(float(value) for value in left_times)
            right_offsets.append(len(right_times_all))
            left_offsets.append(len(left_times_all))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        schema_version=np.array(["0.1.0"]),
        source_path=np.array([str(trials_path)]),
        subject_labels=np.asarray(subject_labels, dtype=str),
        subject_code=np.asarray(subject_codes, dtype=np.int16),
        stimulus_values=np.asarray(stimulus_values, dtype=np.float64),
        choices=np.asarray(choices, dtype=np.int8),
        durations=np.asarray(durations, dtype=np.float64),
        right_offsets=np.asarray(right_offsets, dtype=np.int64),
        left_offsets=np.asarray(left_offsets, dtype=np.int64),
        right_times=np.asarray(right_times_all, dtype=np.float64),
        left_times=np.asarray(left_times_all, dtype=np.float64),
    )
    return {
        "output_path": str(output_path),
        "n_trials": len(choices),
        "n_subjects": len(subject_labels),
        "n_right_clicks": len(right_times_all),
        "n_left_clicks": len(left_times_all),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials-csv", type=Path, default=DEFAULT_TRIALS_PATH)
    parser.add_argument("--out-file", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    summary = build_compact_click_trials(args.trials_csv, args.out_file)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
