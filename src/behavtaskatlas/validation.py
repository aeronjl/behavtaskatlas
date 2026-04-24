from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from behavtaskatlas.models import Dataset, Protocol, TaskFamily, model_from_record


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str


@dataclass(frozen=True)
class ValidationReport:
    records: list[BaseModel]
    issues: list[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not self.issues


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("YAML root must be a mapping")
    return loaded


def load_vocabularies(root: Path) -> dict[str, set[str]]:
    vocab_path = root / "vocabularies" / "core.yaml"
    data = load_yaml(vocab_path)
    vocabularies: dict[str, set[str]] = {}
    for key, values in data.items():
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Vocabulary {key!r} must be a list of strings")
        vocabularies[key] = set(values)
    return vocabularies


def iter_record_paths(root: Path) -> list[Path]:
    record_dirs = ["task_families", "protocols", "datasets", "implementations"]
    paths: list[Path] = []
    for directory in record_dirs:
        record_dir = root / directory
        if record_dir.exists():
            paths.extend(sorted(record_dir.glob("*.yaml")))
    return paths


def validate_repository(root: Path) -> ValidationReport:
    records: list[BaseModel] = []
    issues: list[ValidationIssue] = []

    try:
        vocabularies = load_vocabularies(root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return ValidationReport(records=[], issues=[ValidationIssue(root, str(exc))])

    for path in iter_record_paths(root):
        try:
            data = load_yaml(path)
            records.append(model_from_record(data))
        except (ValueError, ValidationError, yaml.YAMLError) as exc:
            issues.append(ValidationIssue(path, str(exc)))

    ids: dict[str, Path] = {}
    for record in records:
        record_id = getattr(record, "id", None)
        path = _path_for_record(root, record_id)
        if record_id in ids:
            issues.append(ValidationIssue(path, f"Duplicate record id: {record_id}"))
        ids[record_id] = path

    family_ids = {record.id for record in records if isinstance(record, TaskFamily)}
    protocol_ids = {record.id for record in records if isinstance(record, Protocol)}
    dataset_ids = {record.id for record in records if isinstance(record, Dataset)}

    for record in records:
        path = _path_for_record(root, record.id)
        issues.extend(_validate_common_vocab(path, record, vocabularies))

        if isinstance(record, Protocol):
            if record.family_id not in family_ids:
                issues.append(
                    ValidationIssue(path, f"Unknown family_id {record.family_id!r}")
                )
            for dataset_id in record.dataset_ids:
                if dataset_id not in dataset_ids:
                    issues.append(
                        ValidationIssue(path, f"Unknown dataset_id {dataset_id!r}")
                    )

        if isinstance(record, Dataset):
            for protocol_id in record.protocol_ids:
                if protocol_id not in protocol_ids:
                    issues.append(
                        ValidationIssue(path, f"Unknown protocol_id {protocol_id!r}")
                    )

    return ValidationReport(records=records, issues=issues)


def _validate_common_vocab(
    path: Path, record: BaseModel, vocabularies: dict[str, set[str]]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def check(value: str, vocabulary: str, field: str) -> None:
        allowed = vocabularies[vocabulary]
        if value not in allowed:
            issues.append(
                ValidationIssue(
                    path,
                    f"{field}={value!r} is not in vocabulary {vocabulary!r}",
                )
            )

    def check_many(values: list[str], vocabulary: str, field: str) -> None:
        for value in values:
            check(value, vocabulary, field)

    curation_status = getattr(record, "curation_status", None)
    if curation_status:
        check(curation_status, "curation_statuses", "curation_status")

    species = getattr(record, "species", None)
    if species:
        check_many(species, "species", "species")

    if isinstance(record, TaskFamily):
        check_many(record.modalities, "modalities", "modalities")
        check_many(record.common_choice_types, "choice_types", "common_choice_types")
        check_many(
            record.common_response_modalities,
            "response_modalities",
            "common_response_modalities",
        )

    if isinstance(record, Protocol):
        check_many(record.stimulus.modalities, "modalities", "stimulus.modalities")
        check(record.stimulus.evidence_type, "evidence_types", "stimulus.evidence_type")
        check(record.choice.choice_type, "choice_types", "choice.choice_type")
        check_many(
            record.choice.response_modalities,
            "response_modalities",
            "choice.response_modalities",
        )
        check(record.feedback.feedback_type, "feedback_types", "feedback.feedback_type")

    return issues


def _path_for_record(root: Path, record_id: str | None) -> Path:
    if not record_id:
        return root
    for path in iter_record_paths(root):
        try:
            data = load_yaml(path)
        except (OSError, ValueError, yaml.YAMLError):
            continue
        if data.get("id") == record_id:
            return path
    return root

