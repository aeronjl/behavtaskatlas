"""Tests for the cross-record search index."""

from __future__ import annotations

from datetime import date

from behavtaskatlas.models import (
    ChoiceSpec,
    Comparison,
    CurvePoint,
    DataRequest,
    Dataset,
    FeedbackSpec,
    Finding,
    ModelFamily,
    ModelVariant,
    Paper,
    ParameterDefinition,
    Protocol,
    Provenance,
    RequestedDataFile,
    ResultCurve,
    StimulusSpec,
    StratificationKey,
    TaskFamily,
    TrainingSpec,
    VerticalSlice,
    VerticalSliceComparison,
)
from behavtaskatlas.search import build_search_index


def _provenance() -> Provenance:
    return Provenance(
        curators=["behavtaskatlas"],
        created=date(2026, 4, 28),
        updated=date(2026, 4, 28),
    )


def _paper() -> Paper:
    return Paper(
        object_type="paper",
        schema_version="0.1.0",
        id="paper.demo-2024",
        citation="Demo A et al. A great study. Test Journal, 2024.",
        authors=["Demo, Alice"],
        year=2024,
        venue="Test Journal",
        doi="10.1234/demo",
        species=["mouse"],
        n_subjects=4,
        protocol_ids=["protocol.demo"],
        finding_ids=["finding.demo.x"],
        curation_status="data-linked",
        provenance=_provenance(),
    )


def _family() -> TaskFamily:
    return TaskFamily(
        object_type="task_family",
        schema_version="0.1.0",
        id="family.demo",
        name="Random dot motion",
        description="Two-alternative direction discrimination from drifting dots.",
        modalities=["visual"],
        canonical_variables=["coherence"],
        common_choice_types=["2afc"],
        curation_status="literature-curated",
        references=[],
        provenance=_provenance(),
    )


def _protocol() -> Protocol:
    return Protocol(
        object_type="protocol",
        schema_version="0.1.0",
        id="protocol.demo",
        family_id="family.demo",
        name="Demo protocol",
        description="A protocol used by the search test.",
        species=["mouse"],
        curation_status="data-linked",
        stimulus=StimulusSpec(
            modalities=["visual"],
            variables=["contrast"],
            evidence_type="static",
            evidence_schedule="one value per trial",
        ),
        choice=ChoiceSpec(
            choice_type="2afc",
            alternatives=["left", "right"],
            response_modalities=["wheel"],
            action_mapping="turn the wheel",
        ),
        feedback=FeedbackSpec(feedback_type="reward", reward="water"),
        training=TrainingSpec(),
        timing=[],
        references=[],
        provenance=_provenance(),
    )


def _dataset() -> Dataset:
    return Dataset(
        object_type="dataset",
        schema_version="0.1.0",
        id="dataset.demo",
        name="Demo dataset",
        description="A dataset used by the search test.",
        protocol_ids=["protocol.demo"],
        species=["mouse"],
        curation_status="data-linked",
        source_url="https://example.org/data",
        access_notes="Open download.",
        source_data_level="processed-trial",
        provenance=_provenance(),
    )


def _slice() -> VerticalSlice:
    return VerticalSlice(
        object_type="vertical_slice",
        schema_version="0.1.0",
        id="vertical_slice.demo",
        title="Demo slice",
        description="Slice description with the word coherence in it.",
        curation_status="data-linked",
        display_order=1,
        family_id="family.demo",
        protocol_id="protocol.demo",
        dataset_id="dataset.demo",
        report_path="derived/demo/report.html",
        analysis_result_path="derived/demo/result.json",
        comparison=VerticalSliceComparison(
            species="mouse",
            modality="visual",
            stimulus_metric="contrast",
            evidence_type="static",
            choice_type="2afc",
            response_modality="wheel",
            source_data_level="processed-trial",
            analysis_outputs="psychometric",
            data_scope="single-lab",
            canonical_axis="signed contrast",
        ),
        provenance=_provenance(),
    )


def _finding() -> Finding:
    return Finding(
        object_type="finding",
        schema_version="0.1.0",
        id="finding.demo.x",
        paper_id="paper.demo-2024",
        protocol_id="protocol.demo",
        dataset_id="dataset.demo",
        source_data_level="processed-trial",
        stratification=StratificationKey(species="mouse"),
        curve=ResultCurve(
            curve_type="psychometric",
            x_label="Signed contrast",
            x_units="percent",
            y_label="p_right",
            points=[CurvePoint(x=0.0, n=100, y=0.5)],
        ),
        extraction_method="harmonized-pipeline",
        provenance=_provenance(),
    )


def _comparison() -> Comparison:
    return Comparison(
        object_type="comparison",
        schema_version="0.1.0",
        id="comparison.macaque-vs-human",
        title="Macaque vs human RDM",
        question="Do macaques and humans share psychophysical thresholds?",
        framing="Compare psychometric fits across species.",
        finding_ids=["finding.demo.x"],
        color_by="paper",
        hint="Look at threshold and slope.",
        curation_status="data-linked",
        provenance=_provenance(),
    )


def _model_family() -> ModelFamily:
    return ModelFamily(
        object_type="model_family",
        schema_version="0.1.0",
        id="model_family.demo-ddm",
        name="Demo drift diffusion",
        description="A model family for accumulation-to-bound fits.",
        parameter_definitions=[
            ParameterDefinition(
                name="drift_rate",
                symbol="v",
                units="a.u.",
                description="Evidence-dependent drift rate.",
            )
        ],
        applicable_curve_types=["psychometric", "chronometric"],
        requires=["stimulus_value", "choice", "response_time"],
        references=[],
        curation_status="literature-curated",
        provenance=_provenance(),
    )


def _model_variant() -> ModelVariant:
    return ModelVariant(
        object_type="model_variant",
        schema_version="0.1.0",
        id="model_variant.demo-ddm-vanilla",
        family_id="model_family.demo-ddm",
        name="Demo vanilla DDM",
        description="A drift-diffusion variant with fixed starting point.",
        free_parameters=["drift_rate", "boundary", "nondecision_time"],
        fixed_parameters={"z": 0.5},
        requires=["response_time"],
        references=[],
        curation_status="literature-curated",
        provenance=_provenance(),
    )


def _data_request() -> DataRequest:
    return DataRequest(
        object_type="data_request",
        schema_version="0.1.0",
        id="data_request.demo-source-data",
        title="Demo source data request",
        status="ready_to_send",
        priority="high",
        request_type="author_request",
        paper_ids=["paper.demo-2024"],
        protocol_ids=["protocol.demo"],
        model_roadmap_issue_types=["missing_trial_level_source"],
        blocker_type="author_request_raw_trials",
        purpose="Recover missing trial-level source data.",
        blocker_detail="No public trial-level archive was identified.",
        next_action="Send an author request.",
        requested_files=[
            RequestedDataFile(
                name="demo_trials",
                description="Trial-level choices and response times.",
                required=True,
            )
        ],
        curation_status="literature-curated",
        provenance=_provenance(),
    )


def _story() -> dict[str, object]:
    return {
        "id": "story.demo",
        "title": "Demo search story",
        "subtitle": "Cross-record synthesis",
        "body": "A narrative story that links models and findings.",
        "href": "/stories/demo",
        "keywords": ["story", "synthesis"],
    }


def test_build_search_index_covers_every_record_type() -> None:
    index = build_search_index(
        papers=[_paper()],
        families=[_family()],
        protocols=[_protocol()],
        datasets=[_dataset()],
        slices=[_slice()],
        findings=[_finding()],
        comparisons=[_comparison()],
        model_families=[_model_family()],
        model_variants=[_model_variant()],
        data_requests=[_data_request()],
        stories=[_story()],
    )
    assert index["counts"]["total"] == 11
    assert index["counts"] == {
        "paper": 1,
        "task_family": 1,
        "protocol": 1,
        "dataset": 1,
        "vertical_slice": 1,
        "finding": 1,
        "comparison": 1,
        "model": 2,
        "data_request": 1,
        "story": 1,
        "total": 11,
    }
    types = {e["type"] for e in index["entries"]}
    assert types == {
        "paper",
        "task_family",
        "protocol",
        "dataset",
        "vertical_slice",
        "finding",
        "comparison",
        "model",
        "data_request",
        "story",
    }


def test_search_entries_carry_searchable_fields_and_links() -> None:
    index = build_search_index(
        papers=[_paper()],
        families=[_family()],
        protocols=[_protocol()],
        datasets=[_dataset()],
        slices=[_slice()],
        findings=[_finding()],
        comparisons=[_comparison()],
        model_families=[_model_family()],
        model_variants=[_model_variant()],
        data_requests=[_data_request()],
        stories=[_story()],
    )
    by_type = {e["type"]: e for e in index["entries"] if e["type"] != "model"}
    model_entries = [e for e in index["entries"] if e["type"] == "model"]

    paper_entry = by_type["paper"]
    assert paper_entry["href"] == "/papers/demo-2024"
    assert "Demo, Alice" in paper_entry["keywords"]
    assert "10.1234/demo" in paper_entry["keywords"]

    protocol_entry = by_type["protocol"]
    assert protocol_entry["href"] == "/protocols/demo"
    assert "visual" in protocol_entry["keywords"]
    assert "2afc" in protocol_entry["keywords"]

    slice_entry = by_type["vertical_slice"]
    assert slice_entry["href"] == "/slices/demo"
    assert "coherence" in slice_entry["body"]

    finding_entry = by_type["finding"]
    assert finding_entry["href"] == "/findings/demo.x"
    assert "psychometric" in finding_entry["title"]

    comparison_entry = by_type["comparison"]
    assert comparison_entry["href"].startswith("/compare#")
    assert "macaque-vs-human" in comparison_entry["href"]

    model_hrefs = {entry["href"] for entry in model_entries}
    assert "/models#demo-ddm" in model_hrefs
    assert "/models#demo-ddm-vanilla" in model_hrefs
    assert any("drift_rate" in entry["keywords"] for entry in model_entries)

    data_request_entry = by_type["data_request"]
    assert data_request_entry["href"] == "/data_requests/demo-source-data.md"
    assert "missing_trial_level_source" in data_request_entry["keywords"]

    story_entry = by_type["story"]
    assert story_entry["href"] == "/stories/demo"
    assert "synthesis" in story_entry["keywords"]
