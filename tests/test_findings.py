"""Schema-level tests for Paper, Finding, and the validation cross-refs that
keep findings honest about their source-data level and the paper/protocol
graph."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from behavtaskatlas.findings import build_findings_index
from behavtaskatlas.models import (
    CurvePoint,
    Finding,
    Paper,
    Protocol,
    ResultCurve,
    StratificationKey,
    TaskFamily,
    model_from_record,
)
from behavtaskatlas.validation import validate_repository


def _vocab_yaml() -> str:
    return Path("vocabularies/core.yaml").read_text(encoding="utf-8")


def _write_minimal_repo(root: Path) -> None:
    (root / "vocabularies").mkdir()
    (root / "vocabularies" / "core.yaml").write_text(_vocab_yaml(), encoding="utf-8")

    (root / "task_families").mkdir()
    (root / "task_families" / "fam.yaml").write_text(
        yaml.safe_dump(
            {
                "object_type": "task_family",
                "schema_version": "0.1.0",
                "id": "family.demo",
                "name": "Demo family",
                "description": "Demo task family for tests.",
                "modalities": ["visual"],
                "canonical_variables": ["contrast"],
                "common_choice_types": ["2afc"],
                "common_response_modalities": ["wheel"],
                "curation_status": "literature-curated",
                "references": [],
                "provenance": {
                    "curators": ["test"],
                    "created": date.today(),
                    "updated": date.today(),
                },
            }
        ),
        encoding="utf-8",
    )

    (root / "protocols").mkdir()
    (root / "protocols" / "proto.yaml").write_text(
        yaml.safe_dump(
            {
                "object_type": "protocol",
                "schema_version": "0.1.0",
                "id": "protocol.demo",
                "family_id": "family.demo",
                "name": "Demo protocol",
                "description": "Demo protocol for tests.",
                "species": ["mouse"],
                "curation_status": "data-linked",
                "stimulus": {
                    "modalities": ["visual"],
                    "variables": ["contrast"],
                    "evidence_type": "static",
                    "evidence_schedule": "single contrast value per trial",
                },
                "choice": {
                    "choice_type": "2afc",
                    "alternatives": ["left", "right"],
                    "response_modalities": ["wheel"],
                    "action_mapping": "wheel turn",
                },
                "feedback": {
                    "feedback_type": "reward",
                    "reward": "water",
                },
                "timing": [],
                "dataset_ids": ["dataset.demo"],
                "references": [],
                "provenance": {
                    "curators": ["test"],
                    "created": date.today(),
                    "updated": date.today(),
                },
            }
        ),
        encoding="utf-8",
    )

    (root / "datasets").mkdir()
    (root / "datasets" / "ds.yaml").write_text(
        yaml.safe_dump(
            {
                "object_type": "dataset",
                "schema_version": "0.1.0",
                "id": "dataset.demo",
                "name": "Demo dataset",
                "description": "Demo dataset for tests.",
                "protocol_ids": ["protocol.demo"],
                "species": ["mouse"],
                "curation_status": "data-linked",
                "source_url": "https://example.org/data",
                "access_notes": "Demo access notes.",
                "source_data_level": "processed-trial",
                "provenance": {
                    "curators": ["test"],
                    "created": date.today(),
                    "updated": date.today(),
                },
            }
        ),
        encoding="utf-8",
    )

    (root / "papers").mkdir()
    (root / "findings").mkdir()


def _paper_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "object_type": "paper",
        "schema_version": "0.1.0",
        "id": "paper.demo-2024",
        "citation": "Demo et al. 2024",
        "authors": ["Demo, A."],
        "year": 2024,
        "venue": "Test Journal",
        "doi": "10.1234/demo",
        "species": ["mouse"],
        "n_subjects": 4,
        "protocol_ids": ["protocol.demo"],
        "dataset_ids": ["dataset.demo"],
        "finding_ids": ["finding.demo-2024.psychometric"],
        "curation_status": "data-linked",
        "provenance": {
            "curators": ["test"],
            "created": date.today(),
            "updated": date.today(),
        },
    }
    base.update(overrides)
    return base


def _finding_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "object_type": "finding",
        "schema_version": "0.1.0",
        "id": "finding.demo-2024.psychometric",
        "paper_id": "paper.demo-2024",
        "protocol_id": "protocol.demo",
        "dataset_id": "dataset.demo",
        "source_data_level": "processed-trial",
        "n_trials": 1200,
        "n_subjects": 4,
        "stratification": {"species": "mouse"},
        "curve": {
            "curve_type": "psychometric",
            "x_label": "Signed contrast",
            "x_units": "percent",
            "y_label": "p_right",
            "points": [
                {"x": -50.0, "n": 100, "y": 0.05},
                {"x": -25.0, "n": 100, "y": 0.18},
                {"x": 0.0, "n": 100, "y": 0.50},
                {"x": 25.0, "n": 100, "y": 0.82},
                {"x": 50.0, "n": 100, "y": 0.96},
            ],
        },
        "extraction_method": "harmonized-pipeline",
        "provenance": {
            "curators": ["test"],
            "created": date.today(),
            "updated": date.today(),
        },
    }
    base.update(overrides)
    return base


def _write_paper_finding(root: Path) -> None:
    (root / "papers" / "p.yaml").write_text(
        yaml.safe_dump(_paper_payload()), encoding="utf-8"
    )
    (root / "findings" / "f.yaml").write_text(
        yaml.safe_dump(_finding_payload()), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Pydantic shape
# ---------------------------------------------------------------------------


def test_paper_model_validates_minimal_record() -> None:
    record = model_from_record(_paper_payload())
    assert isinstance(record, Paper)
    assert record.year == 2024
    assert record.protocol_ids == ["protocol.demo"]


def test_finding_model_validates_minimal_record() -> None:
    record = model_from_record(_finding_payload())
    assert isinstance(record, Finding)
    assert record.curve.curve_type == "psychometric"
    assert len(record.curve.points) == 5
    assert record.stratification.species == "mouse"


def test_finding_rejects_unknown_curve_type() -> None:
    with pytest.raises(ValidationError):
        model_from_record(
            _finding_payload(
                curve={
                    "curve_type": "not-a-real-type",
                    "x_label": "x",
                    "x_units": "x",
                    "y_label": "y",
                    "points": [],
                }
            )
        )


def test_finding_rejects_unknown_extraction_method() -> None:
    with pytest.raises(ValidationError):
        model_from_record(_finding_payload(extraction_method="copy-paste"))


def test_curve_point_keeps_optional_uncertainty_fields() -> None:
    point = CurvePoint(x=0.0, n=80, y=0.5, y_lower=0.4, y_upper=0.6, se=0.05)
    assert point.y_upper == 0.6


def test_stratification_key_is_optional_everywhere() -> None:
    key = StratificationKey()
    assert key.species is None


def test_result_curve_round_trips() -> None:
    curve = ResultCurve(
        curve_type="chronometric",
        x_label="abs coh",
        x_units="percent",
        y_label="median rt",
        points=[CurvePoint(x=10.0, n=50, y=0.45)],
    )
    assert curve.curve_type == "chronometric"


# ---------------------------------------------------------------------------
# Cross-reference validation against a tmp_path repo
# ---------------------------------------------------------------------------


def test_validation_accepts_paper_and_finding_when_consistent(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    _write_paper_finding(tmp_path)
    report = validate_repository(tmp_path)
    assert report.ok, [
        f"{issue.path}: {issue.message}" for issue in report.issues
    ]


def test_validation_flags_finding_with_unknown_paper(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    (tmp_path / "papers" / "p.yaml").write_text(
        yaml.safe_dump(_paper_payload()), encoding="utf-8"
    )
    (tmp_path / "findings" / "f.yaml").write_text(
        yaml.safe_dump(_finding_payload(paper_id="paper.does-not-exist")),
        encoding="utf-8",
    )
    report = validate_repository(tmp_path)
    messages = [issue.message for issue in report.issues]
    assert any("Unknown paper_id" in m for m in messages)


def test_validation_flags_source_data_level_mismatch_with_dataset(
    tmp_path: Path,
) -> None:
    _write_minimal_repo(tmp_path)
    (tmp_path / "papers" / "p.yaml").write_text(
        yaml.safe_dump(_paper_payload()), encoding="utf-8"
    )
    (tmp_path / "findings" / "f.yaml").write_text(
        yaml.safe_dump(_finding_payload(source_data_level="raw-trial")),
        encoding="utf-8",
    )
    report = validate_repository(tmp_path)
    messages = [issue.message for issue in report.issues]
    assert any("source_data_level" in m and "does not match" in m for m in messages)


def test_validation_flags_paper_finding_id_reciprocity(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    (tmp_path / "papers" / "p.yaml").write_text(
        yaml.safe_dump(_paper_payload(finding_ids=[])),
        encoding="utf-8",
    )
    (tmp_path / "findings" / "f.yaml").write_text(
        yaml.safe_dump(_finding_payload()), encoding="utf-8"
    )
    report = validate_repository(tmp_path)
    messages = [issue.message for issue in report.issues]
    assert any(
        "finding_ids missing" in m and "finding.demo-2024.psychometric" in m
        for m in messages
    )


def test_build_findings_index_denormalizes_paper_and_protocol() -> None:
    paper = model_from_record(_paper_payload())
    finding = model_from_record(_finding_payload())
    protocol = Protocol(
        object_type="protocol",
        schema_version="0.1.0",
        id="protocol.demo",
        family_id="family.demo",
        name="Demo protocol",
        description="Demo for index test.",
        species=["mouse"],
        curation_status="data-linked",
        stimulus={
            "modalities": ["visual"],
            "variables": ["contrast"],
            "evidence_type": "static",
            "evidence_schedule": "single contrast value per trial",
        },
        choice={
            "choice_type": "2afc",
            "alternatives": ["left", "right"],
            "response_modalities": ["wheel"],
            "action_mapping": "wheel turn",
        },
        feedback={"feedback_type": "reward"},
        timing=[],
        references=[],
        provenance={
            "curators": ["test"],
            "created": date.today(),
            "updated": date.today(),
        },
    )
    family = TaskFamily(
        object_type="task_family",
        schema_version="0.1.0",
        id="family.demo",
        name="Demo family",
        description="Test family.",
        modalities=["visual"],
        canonical_variables=["contrast"],
        common_choice_types=["2afc"],
        curation_status="literature-curated",
        references=[],
        provenance={
            "curators": ["test"],
            "created": date.today(),
            "updated": date.today(),
        },
    )

    payload = build_findings_index(
        papers=[paper],
        findings=[finding],
        protocols=[protocol],
        families=[family],
    )

    assert payload["counts"]["papers"] == 1
    assert payload["counts"]["finding_papers"] == 1
    assert payload["counts"]["findings"] == 1
    assert payload["counts"]["psychometric"] == 1
    entry = payload["findings"][0]
    assert entry["finding_id"] == "finding.demo-2024.psychometric"
    assert entry["paper_citation"] == "Demo et al. 2024"
    assert entry["paper_year"] == 2024
    assert entry["protocol_name"] == "Demo protocol"
    assert entry["family_name"] == "Demo family"
    assert entry["modalities"] == ["visual"]
    assert entry["evidence_type"] == "static"
    assert entry["response_modality"] == "wheel"
    assert entry["source_data_level"] == "processed-trial"
    assert len(entry["points"]) == 5
    assert entry["points"][0]["x"] == -50.0


def test_validation_flags_finding_protocol_not_declared_by_paper(
    tmp_path: Path,
) -> None:
    _write_minimal_repo(tmp_path)
    (tmp_path / "papers" / "p.yaml").write_text(
        yaml.safe_dump(_paper_payload(protocol_ids=[])),
        encoding="utf-8",
    )
    (tmp_path / "findings" / "f.yaml").write_text(
        yaml.safe_dump(_finding_payload()), encoding="utf-8"
    )
    report = validate_repository(tmp_path)
    messages = [issue.message for issue in report.issues]
    assert any("not declared by paper" in m for m in messages)


# ---------------------------------------------------------------------------
# Comparison cross-reference checks
# ---------------------------------------------------------------------------


def _comparison_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "object_type": "comparison",
        "schema_version": "0.1.0",
        "id": "comparison.demo",
        "title": "Demo comparison",
        "question": "Does demo finding A differ from demo finding B?",
        "framing": "Two demo findings stratified by condition.",
        "finding_ids": [
            "finding.demo-2024.psychometric",
            "finding.demo-2024.psychometric.b",
        ],
        "color_by": "paper",
        "hint": "Compare Δμ.",
        "display_order": 10,
        "curation_status": "data-linked",
        "provenance": {
            "curators": ["test"],
            "created": date.today(),
            "updated": date.today(),
        },
    }
    base.update(overrides)
    return base


def test_validation_accepts_comparison_when_finding_ids_resolve(
    tmp_path: Path,
) -> None:
    _write_minimal_repo(tmp_path)
    second_finding = _finding_payload(
        id="finding.demo-2024.psychometric.b",
        stratification={"condition": "demo-b"},
    )
    paper = _paper_payload(
        finding_ids=[
            "finding.demo-2024.psychometric",
            "finding.demo-2024.psychometric.b",
        ],
    )
    (tmp_path / "papers" / "p.yaml").write_text(yaml.safe_dump(paper), encoding="utf-8")
    (tmp_path / "findings" / "a.yaml").write_text(
        yaml.safe_dump(_finding_payload()), encoding="utf-8"
    )
    (tmp_path / "findings" / "b.yaml").write_text(
        yaml.safe_dump(second_finding), encoding="utf-8"
    )
    (tmp_path / "comparisons").mkdir()
    (tmp_path / "comparisons" / "demo.yaml").write_text(
        yaml.safe_dump(_comparison_payload()), encoding="utf-8"
    )
    report = validate_repository(tmp_path)
    assert report.ok, [
        f"{issue.path}: {issue.message}" for issue in report.issues
    ]


def test_validation_flags_comparison_with_unknown_finding_id(
    tmp_path: Path,
) -> None:
    _write_minimal_repo(tmp_path)
    (tmp_path / "papers" / "p.yaml").write_text(
        yaml.safe_dump(_paper_payload()), encoding="utf-8"
    )
    (tmp_path / "findings" / "f.yaml").write_text(
        yaml.safe_dump(_finding_payload()), encoding="utf-8"
    )
    (tmp_path / "comparisons").mkdir()
    (tmp_path / "comparisons" / "broken.yaml").write_text(
        yaml.safe_dump(
            _comparison_payload(
                finding_ids=[
                    "finding.demo-2024.psychometric",
                    "finding.does-not-exist",
                ],
            )
        ),
        encoding="utf-8",
    )
    report = validate_repository(tmp_path)
    messages = [issue.message for issue in report.issues]
    assert any(
        "Unknown finding_id 'finding.does-not-exist'" in m for m in messages
    )


def test_validation_flags_comparison_with_too_few_findings(
    tmp_path: Path,
) -> None:
    _write_minimal_repo(tmp_path)
    (tmp_path / "papers" / "p.yaml").write_text(
        yaml.safe_dump(_paper_payload()), encoding="utf-8"
    )
    (tmp_path / "findings" / "f.yaml").write_text(
        yaml.safe_dump(_finding_payload()), encoding="utf-8"
    )
    (tmp_path / "comparisons").mkdir()
    (tmp_path / "comparisons" / "lonely.yaml").write_text(
        yaml.safe_dump(
            _comparison_payload(
                finding_ids=["finding.demo-2024.psychometric"],
            )
        ),
        encoding="utf-8",
    )
    report = validate_repository(tmp_path)
    messages = [issue.message for issue in report.issues]
    assert any("at least two findings" in m for m in messages)
