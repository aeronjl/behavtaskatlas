from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from behavtaskatlas.models import (
    Comparison,
    Dataset,
    Finding,
    Paper,
    Protocol,
    TaskFamily,
    VerticalSlice,
    model_from_record,
)


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
    record_dirs = [
        "task_families",
        "protocols",
        "datasets",
        "implementations",
        "papers",
        "findings",
        "comparisons",
    ]
    paths: list[Path] = []
    for directory in record_dirs:
        record_dir = root / directory
        if record_dir.exists():
            paths.extend(sorted(record_dir.glob("*.yaml")))
    slice_dir = root / "vertical_slices"
    if slice_dir.exists():
        paths.extend(sorted(slice_dir.glob("*/slice.yaml")))
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
    protocol_by_id = {record.id: record for record in records if isinstance(record, Protocol)}
    dataset_by_id = {record.id: record for record in records if isinstance(record, Dataset)}
    slice_by_id = {
        record.id: record for record in records if isinstance(record, VerticalSlice)
    }
    paper_ids = {record.id for record in records if isinstance(record, Paper)}
    paper_by_id = {record.id: record for record in records if isinstance(record, Paper)}
    findings_by_paper: dict[str, list[Finding]] = {}
    finding_ids = set()
    for record in records:
        if isinstance(record, Finding):
            findings_by_paper.setdefault(record.paper_id, []).append(record)
            finding_ids.add(record.id)

    for record in records:
        path = _path_for_record(root, record.id)
        issues.extend(_validate_common_vocab(path, record, vocabularies))

        if isinstance(record, Protocol):
            if record.family_id not in family_ids:
                issues.append(
                    ValidationIssue(path, f"Unknown family_id {record.family_id!r}")
                )
            if record.template_protocol_id:
                if record.template_protocol_id == record.id:
                    issues.append(
                        ValidationIssue(
                            path,
                            "template_protocol_id must not reference the same protocol",
                        )
                    )
                elif record.template_protocol_id not in protocol_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"Unknown template_protocol_id {record.template_protocol_id!r}",
                        )
                    )
            elif record.protocol_scope == "concrete" and len(record.species) > 1:
                issues.append(
                    ValidationIssue(
                        path,
                        "Concrete protocols with multiple species should declare "
                        "template_protocol_id or use protocol_scope='template'",
                    )
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

        if isinstance(record, VerticalSlice):
            if record.family_id not in family_ids:
                issues.append(ValidationIssue(path, f"Unknown family_id {record.family_id!r}"))
            protocol = protocol_by_id.get(record.protocol_id)
            if protocol is None:
                issues.append(
                    ValidationIssue(path, f"Unknown protocol_id {record.protocol_id!r}")
                )
            elif protocol.family_id != record.family_id:
                issues.append(
                    ValidationIssue(
                        path,
                        f"protocol_id {record.protocol_id!r} does not belong to "
                        f"family_id {record.family_id!r}",
                    )
                )
            dataset = dataset_by_id.get(record.dataset_id)
            if dataset is None:
                issues.append(
                    ValidationIssue(path, f"Unknown dataset_id {record.dataset_id!r}")
                )
            elif record.protocol_id not in dataset.protocol_ids:
                issues.append(
                    ValidationIssue(
                        path,
                        f"dataset_id {record.dataset_id!r} does not reference "
                        f"protocol_id {record.protocol_id!r}",
                    )
                )

        if isinstance(record, Paper):
            for protocol_id in record.protocol_ids:
                if protocol_id not in protocol_ids:
                    issues.append(
                        ValidationIssue(path, f"Unknown protocol_id {protocol_id!r}")
                    )
            for dataset_id in record.dataset_ids:
                if dataset_id not in dataset_ids:
                    issues.append(
                        ValidationIssue(path, f"Unknown dataset_id {dataset_id!r}")
                    )
            declared_findings = set(record.finding_ids)
            actual_findings = {
                finding.id for finding in findings_by_paper.get(record.id, [])
            }
            missing_in_paper = actual_findings - declared_findings
            extra_in_paper = declared_findings - actual_findings
            if missing_in_paper:
                joined = ", ".join(sorted(missing_in_paper))
                issues.append(
                    ValidationIssue(
                        path,
                        f"Paper.finding_ids missing {joined!r}; findings point at this paper",
                    )
                )
            if extra_in_paper:
                joined = ", ".join(sorted(extra_in_paper))
                issues.append(
                    ValidationIssue(
                        path,
                        f"Paper.finding_ids references unknown {joined!r}",
                    )
                )

        if isinstance(record, Comparison):
            seen_local: set[str] = set()
            for fid in record.finding_ids:
                if fid not in finding_ids:
                    issues.append(
                        ValidationIssue(path, f"Unknown finding_id {fid!r}")
                    )
                if fid in seen_local:
                    issues.append(
                        ValidationIssue(
                            path, f"Duplicate finding_id {fid!r} in comparison"
                        )
                    )
                seen_local.add(fid)
            if len(record.finding_ids) < 2:
                issues.append(
                    ValidationIssue(
                        path,
                        "Comparison must reference at least two findings",
                    )
                )

        if isinstance(record, Finding):
            if record.paper_id not in paper_ids:
                issues.append(
                    ValidationIssue(path, f"Unknown paper_id {record.paper_id!r}")
                )
            protocol = protocol_by_id.get(record.protocol_id)
            if protocol is None:
                issues.append(
                    ValidationIssue(path, f"Unknown protocol_id {record.protocol_id!r}")
                )
            paper = paper_by_id.get(record.paper_id)
            if paper is not None and record.protocol_id not in paper.protocol_ids:
                issues.append(
                    ValidationIssue(
                        path,
                        f"Finding.protocol_id {record.protocol_id!r} not declared by "
                        f"paper {record.paper_id!r}",
                    )
                )
            if record.dataset_id is not None:
                dataset = dataset_by_id.get(record.dataset_id)
                if dataset is None:
                    issues.append(
                        ValidationIssue(
                            path, f"Unknown dataset_id {record.dataset_id!r}"
                        )
                    )
                elif record.source_data_level != dataset.source_data_level:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"Finding.source_data_level {record.source_data_level!r} "
                            f"does not match dataset {record.dataset_id!r} "
                            f"({dataset.source_data_level!r})",
                        )
                    )
            if record.slice_id is not None:
                slice_record = slice_by_id.get(record.slice_id)
                if slice_record is None:
                    issues.append(
                        ValidationIssue(path, f"Unknown slice_id {record.slice_id!r}")
                    )
                else:
                    if slice_record.protocol_id != record.protocol_id:
                        issues.append(
                            ValidationIssue(
                                path,
                                f"Finding.slice_id {record.slice_id!r} protocol "
                                f"{slice_record.protocol_id!r} does not match "
                                f"finding protocol {record.protocol_id!r}",
                            )
                        )
                    if (
                        record.dataset_id is not None
                        and slice_record.dataset_id != record.dataset_id
                    ):
                        issues.append(
                            ValidationIssue(
                                path,
                                f"Finding.slice_id {record.slice_id!r} dataset "
                                f"{slice_record.dataset_id!r} does not match "
                                f"finding dataset {record.dataset_id!r}",
                            )
                        )
                    if (
                        record.source_data_level
                        != slice_record.comparison.source_data_level
                    ):
                        issues.append(
                            ValidationIssue(
                                path,
                                f"Finding.source_data_level {record.source_data_level!r} "
                                f"does not match slice {record.slice_id!r} "
                                f"({slice_record.comparison.source_data_level!r})",
                            )
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

    if isinstance(record, Dataset):
        check(record.source_data_level, "source_data_levels", "source_data_level")

    if isinstance(record, VerticalSlice):
        check(record.comparison.species, "species", "comparison.species")
        check(record.comparison.modality, "modalities", "comparison.modality")
        check(
            record.comparison.evidence_type,
            "evidence_types",
            "comparison.evidence_type",
        )
        check(record.comparison.choice_type, "choice_types", "comparison.choice_type")
        check(
            record.comparison.response_modality,
            "response_modalities",
            "comparison.response_modality",
        )
        check(
            record.comparison.source_data_level,
            "source_data_levels",
            "comparison.source_data_level",
        )

    if isinstance(record, Finding):
        check(record.source_data_level, "source_data_levels", "source_data_level")
        check(record.extraction_method, "extraction_methods", "extraction_method")
        check(record.curve.curve_type, "curve_types", "curve.curve_type")
        if record.stratification.species is not None:
            check(record.stratification.species, "species", "stratification.species")
        if record.stratification.response_modality is not None:
            check(
                record.stratification.response_modality,
                "response_modalities",
                "stratification.response_modality",
            )

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
