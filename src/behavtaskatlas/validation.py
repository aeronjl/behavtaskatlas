from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from behavtaskatlas.data_requests import validate_data_request_status_event_state
from behavtaskatlas.models import (
    Comparison,
    DataRequest,
    Dataset,
    Finding,
    ModelFamily,
    ModelFit,
    ModelVariant,
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
        "data_requests",
        "model_families",
        "model_variants",
        "model_fits",
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
    path_by_record_object: dict[int, Path] = {}
    issues: list[ValidationIssue] = []

    try:
        vocabularies = load_vocabularies(root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return ValidationReport(records=[], issues=[ValidationIssue(root, str(exc))])

    for path in iter_record_paths(root):
        try:
            data = load_yaml(path)
            record = model_from_record(data)
            records.append(record)
            path_by_record_object[id(record)] = path
        except (ValueError, ValidationError, yaml.YAMLError) as exc:
            issues.append(ValidationIssue(path, str(exc)))

    ids: dict[str, Path] = {}
    for record in records:
        record_id = getattr(record, "id", None)
        path = path_by_record_object.get(id(record), root)
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
    model_family_ids = {r.id for r in records if isinstance(r, ModelFamily)}
    model_family_by_id = {r.id: r for r in records if isinstance(r, ModelFamily)}
    model_variant_by_id = {r.id: r for r in records if isinstance(r, ModelVariant)}
    model_fit_ids = {r.id for r in records if isinstance(r, ModelFit)}
    findings_by_paper: dict[str, list[Finding]] = {}
    finding_ids = set()
    for record in records:
        if isinstance(record, Finding):
            findings_by_paper.setdefault(record.paper_id, []).append(record)
            finding_ids.add(record.id)

    for record in records:
        path = path_by_record_object.get(id(record), root)
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
            seen_fits: set[str] = set()
            for mid in record.model_fit_ids:
                if mid not in model_fit_ids:
                    issues.append(
                        ValidationIssue(
                            path, f"Unknown model_fit_id {mid!r} in comparison"
                        )
                    )
                if mid in seen_fits:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"Duplicate model_fit_id {mid!r} in comparison",
                        )
                    )
                seen_fits.add(mid)
            total_refs = len(record.finding_ids) + len(record.model_fit_ids)
            if total_refs < 2:
                issues.append(
                    ValidationIssue(
                        path,
                        "Comparison must reference at least two findings or "
                        "model fits",
                    )
                )

        if isinstance(record, DataRequest):
            for dataset_id in record.dataset_ids:
                if dataset_id not in dataset_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"DataRequest.dataset_ids references unknown {dataset_id!r}",
                        )
                    )
            for paper_id in record.paper_ids:
                if paper_id not in paper_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"DataRequest.paper_ids references unknown {paper_id!r}",
                        )
                    )
            for protocol_id in record.protocol_ids:
                if protocol_id not in protocol_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"DataRequest.protocol_ids references unknown {protocol_id!r}",
                        )
                    )
            for slice_id in record.slice_ids:
                if slice_id not in slice_by_id:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"DataRequest.slice_ids references unknown {slice_id!r}",
                        )
                    )
            for finding_id in record.finding_ids:
                if finding_id not in finding_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"DataRequest.finding_ids references unknown {finding_id!r}",
                        )
                    )
            if not (
                record.dataset_ids
                or record.paper_ids
                or record.protocol_ids
                or record.slice_ids
                or record.finding_ids
            ):
                issues.append(
                    ValidationIssue(
                        path,
                        "DataRequest must reference at least one dataset, paper, "
                        "protocol, slice, or finding",
                    )
                )
            if not record.requested_files:
                issues.append(
                    ValidationIssue(path, "DataRequest must request at least one file")
                )
            issues.extend(_validate_data_request_status_events(path, record))

        if isinstance(record, ModelVariant):
            if record.family_id not in model_family_ids:
                issues.append(
                    ValidationIssue(
                        path,
                        f"ModelVariant.family_id references unknown "
                        f"{record.family_id!r}",
                    )
                )
            else:
                family = model_family_by_id[record.family_id]
                family_param_names = {
                    p.name for p in family.parameter_definitions
                }
                additional_param_names = {
                    p.name for p in record.additional_parameters
                }
                allowed = family_param_names | additional_param_names
                for fp in record.free_parameters:
                    if fp not in allowed:
                        issues.append(
                            ValidationIssue(
                                path,
                                f"ModelVariant.free_parameters {fp!r} not in "
                                f"family {record.family_id!r} parameters",
                            )
                        )
                for fp in record.fixed_parameters:
                    if fp not in allowed:
                        issues.append(
                            ValidationIssue(
                                path,
                                f"ModelVariant.fixed_parameters {fp!r} not in "
                                f"family {record.family_id!r} parameters",
                            )
                        )
                overlap = set(record.free_parameters) & set(
                    record.fixed_parameters.keys()
                )
                if overlap:
                    joined = ", ".join(sorted(overlap))
                    issues.append(
                        ValidationIssue(
                            path,
                            f"ModelVariant has parameters in both free and "
                            f"fixed: {joined}",
                        )
                    )
                for fp, pattern in record.parameter_patterns.items():
                    if fp not in record.free_parameters:
                        issues.append(
                            ValidationIssue(
                                path,
                                f"ModelVariant.parameter_patterns key {fp!r} "
                                "must be declared in free_parameters",
                            )
                        )
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        issues.append(
                            ValidationIssue(
                                path,
                                f"ModelVariant.parameter_patterns {fp!r} has "
                                f"invalid regex: {exc}",
                            )
                        )

        if isinstance(record, ModelFit):
            variant = model_variant_by_id.get(record.variant_id)
            if variant is None:
                issues.append(
                    ValidationIssue(
                        path,
                        f"ModelFit.variant_id references unknown "
                        f"{record.variant_id!r}",
                    )
                )
            else:
                got = set(record.parameters.keys())
                expected = set(variant.free_parameters)
                patterned_free_parameters = set(variant.parameter_patterns)
                compiled_patterns: list[tuple[str, re.Pattern[str]]] = []
                for fp, pattern in variant.parameter_patterns.items():
                    try:
                        compiled_patterns.append((fp, re.compile(pattern)))
                    except re.error:
                        continue
                missing = expected - got - patterned_free_parameters
                extra = {
                    parameter
                    for parameter in got - expected
                    if not any(
                        pattern.fullmatch(parameter) for _, pattern in compiled_patterns
                    )
                }
                for fp, pattern in compiled_patterns:
                    if not any(pattern.fullmatch(parameter) for parameter in got):
                        issues.append(
                            ValidationIssue(
                                path,
                                f"ModelFit has no concrete parameters matching "
                                f"variant free parameter pattern {fp!r}",
                            )
                        )
                if missing:
                    joined = ", ".join(sorted(missing))
                    issues.append(
                        ValidationIssue(
                            path,
                            f"ModelFit missing variant free parameters: {joined}",
                        )
                    )
                if extra:
                    joined = ", ".join(sorted(extra))
                    issues.append(
                        ValidationIssue(
                            path,
                            f"ModelFit has parameters not declared free in "
                            f"variant {record.variant_id!r}: {joined}",
                        )
                    )
            if not record.finding_ids:
                issues.append(
                    ValidationIssue(
                        path, "ModelFit must reference at least one finding_id"
                    )
                )
            for fid in record.finding_ids:
                if fid not in finding_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            f"ModelFit.finding_ids references unknown {fid!r}",
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


def _validate_data_request_status_events(
    path: Path,
    record: DataRequest,
) -> list[ValidationIssue]:
    return [
        ValidationIssue(path, message)
        for message in validate_data_request_status_event_state(record)
    ]


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

    if isinstance(record, DataRequest):
        if not record.id.startswith("data_request."):
            issues.append(
                ValidationIssue(path, "DataRequest id should start with 'data_request.'")
            )

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
