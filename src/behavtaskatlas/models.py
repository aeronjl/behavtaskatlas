from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Reference(StrictModel):
    id: str
    citation: str
    url: str | None = None
    doi: str | None = None
    notes: str | None = None


class Provenance(StrictModel):
    curators: list[str] = Field(default_factory=list)
    created: date
    updated: date
    source_notes: str | None = None


class Phase(StrictModel):
    name: str
    duration: str
    description: str | None = None
    contingent_on: str | None = None


class StimulusSpec(StrictModel):
    modalities: list[str]
    variables: list[str]
    evidence_type: str
    evidence_schedule: str
    units: list[str] = Field(default_factory=list)
    notes: str | None = None


class ChoiceSpec(StrictModel):
    choice_type: str
    alternatives: list[str]
    response_modalities: list[str]
    action_mapping: str
    notes: str | None = None


class FeedbackSpec(StrictModel):
    feedback_type: str
    reward: str | None = None
    penalty: str | None = None
    notes: str | None = None


class TrainingSpec(StrictModel):
    stages: list[str] = Field(default_factory=list)
    notes: str | None = None


class InterpretationClaim(StrictModel):
    label: str
    source: str
    confidence: Literal["low", "medium", "high"]
    caveat: str | None = None


class TaskFamily(StrictModel):
    object_type: Literal["task_family"]
    schema_version: str
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str
    modalities: list[str]
    canonical_variables: list[str]
    common_choice_types: list[str]
    common_response_modalities: list[str] = Field(default_factory=list)
    curation_status: str
    references: list[Reference]
    provenance: Provenance
    notes: str | None = None


class Protocol(StrictModel):
    object_type: Literal["protocol"]
    schema_version: str
    id: str
    family_id: str
    protocol_scope: Literal["template", "concrete"] = "concrete"
    template_protocol_id: str | None = None
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str
    species: list[str]
    curation_status: str
    stimulus: StimulusSpec
    choice: ChoiceSpec
    timing: list[Phase]
    feedback: FeedbackSpec
    training: TrainingSpec = Field(default_factory=TrainingSpec)
    apparatus: list[str] = Field(default_factory=list)
    software: list[str] = Field(default_factory=list)
    dataset_ids: list[str] = Field(default_factory=list)
    implementation_ids: list[str] = Field(default_factory=list)
    expected_analyses: list[str] = Field(default_factory=list)
    interpretive_claims: list[InterpretationClaim] = Field(default_factory=list)
    references: list[Reference]
    provenance: Provenance
    open_questions: list[str] = Field(default_factory=list)


class Dataset(StrictModel):
    object_type: Literal["dataset"]
    schema_version: str
    id: str
    name: str
    description: str
    protocol_ids: list[str]
    species: list[str]
    curation_status: str
    source_url: str
    access_notes: str
    source_data_level: str
    license: str | None = None
    data_formats: list[str] = Field(default_factory=list)
    expected_trial_table_mapping: dict[str, str] = Field(default_factory=dict)
    references: list[Reference] = Field(default_factory=list)
    provenance: Provenance
    caveats: list[str] = Field(default_factory=list)


class Implementation(StrictModel):
    object_type: Literal["implementation"]
    schema_version: str
    id: str
    name: str
    protocol_ids: list[str]
    description: str
    language_or_platform: str
    source_url: str | None = None
    commit_or_version: str | None = None
    curation_status: str
    references: list[Reference] = Field(default_factory=list)
    provenance: Provenance


class ArtifactLinkSpec(StrictModel):
    label: str
    path: str
    path_type: Literal["derived", "repository"] = "derived"


class VerticalSliceComparison(StrictModel):
    species: str
    modality: str
    stimulus_metric: str
    evidence_type: str
    choice_type: str
    response_modality: str
    source_data_level: str
    analysis_outputs: str
    data_scope: str
    canonical_axis: str


class VerticalSlice(StrictModel):
    object_type: Literal["vertical_slice"]
    schema_version: str
    id: str
    title: str
    description: str
    curation_status: str
    display_order: int
    family_id: str
    protocol_id: str
    dataset_id: str
    report_path: str
    analysis_result_path: str
    primary_artifact_path: str | None = None
    primary_artifact_label: str | None = None
    artifact_links: list[ArtifactLinkSpec] = Field(default_factory=list)
    comparison: VerticalSliceComparison
    provenance: Provenance
    notes: str | None = None


class CanonicalTrial(StrictModel):
    protocol_id: str
    dataset_id: str | None = None
    subject_id: str | None = None
    session_id: str
    trial_index: int
    stimulus_modality: str
    stimulus_value: float | None = None
    stimulus_units: str | None = None
    stimulus_side: Literal["left", "right", "none", "unknown"] = "unknown"
    evidence_strength: float | None = None
    evidence_units: str | None = None
    choice: Literal["left", "right", "go", "withhold", "no-response", "unknown"]
    correct: bool | None = None
    response_time: float | None = None
    response_time_origin: str | None = None
    feedback: Literal["reward", "error", "none", "unknown"] = "unknown"
    reward: float | None = None
    reward_units: str | None = None
    block_id: str | None = None
    prior_context: str | None = None
    training_stage: str | None = None
    task_variables: dict[str, Any] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)


class ManifestLink(StrictModel):
    label: str
    href: str


class ManifestMetric(StrictModel):
    label: str
    value: Any = None


class ManifestComparisonRow(StrictModel):
    slice_id: str
    title: str
    family_id: str
    protocol_id: str
    dataset_id: str
    species: str
    modality: str
    stimulus_metric: str
    evidence_type: str
    choice_type: str
    response_modality: str
    source_data_level: str
    analysis_outputs: str
    data_scope: str
    canonical_axis: str
    report_status: str
    artifact_status: str
    primary_link: str | None = None
    trial_count: int | None = None


class ManifestSlice(StrictModel):
    id: str
    title: str
    family_id: str
    protocol_id: str
    dataset_id: str
    status_label: str
    report_status: str
    artifact_status: str
    description: str
    primary_link: str | None = None
    primary_link_label: str
    metrics: list[ManifestMetric] = Field(default_factory=list)
    links: list[ManifestLink] = Field(default_factory=list)
    comparison: VerticalSliceComparison


class ReportManifest(StrictModel):
    manifest_schema_version: str
    title: str
    generated_at: str
    behavtaskatlas_commit: str | None = None
    behavtaskatlas_git_dirty: bool | None = None
    derived_dir: str
    manifest_link: str
    catalog_link: str | None = None
    graph_link: str | None = None
    curation_queue_link: str | None = None
    health: dict[str, Any] = Field(default_factory=dict)
    comparison_rows: list[ManifestComparisonRow]
    slices: list[ManifestSlice]


class CatalogFamilyRow(StrictModel):
    family_id: str
    name: str
    modalities: list[str] = Field(default_factory=list)
    choice_types: list[str] = Field(default_factory=list)
    curation_status: str
    protocol_count: int
    dataset_count: int
    slice_count: int


class CatalogProtocolRow(StrictModel):
    protocol_id: str
    detail_link: str
    name: str
    family_id: str
    family_name: str | None = None
    protocol_scope: Literal["template", "concrete"] = "concrete"
    template_protocol_id: str | None = None
    species: list[str] = Field(default_factory=list)
    modalities: list[str] = Field(default_factory=list)
    evidence_type: str
    choice_type: str
    response_modalities: list[str] = Field(default_factory=list)
    declared_dataset_ids: list[str] = Field(default_factory=list)
    dataset_ids: list[str] = Field(default_factory=list)
    slice_ids: list[str] = Field(default_factory=list)
    curation_status: str
    report_status: str


class CatalogLinkedDataset(StrictModel):
    dataset_id: str
    detail_link: str
    name: str
    source_url: str
    source_data_level: str
    license: str | None = None
    curation_status: str


class CatalogLinkedProtocol(StrictModel):
    protocol_id: str
    detail_link: str
    name: str
    family_name: str | None = None
    protocol_scope: Literal["template", "concrete"] = "concrete"
    species: list[str] = Field(default_factory=list)
    evidence_type: str
    choice_type: str
    report_status: str


class CatalogLinkedSlice(StrictModel):
    slice_id: str
    title: str
    report_status: str
    artifact_status: str
    source_data_level: str | None = None
    primary_link: str | None = None


class CatalogProtocolDetail(StrictModel):
    protocol_id: str
    detail_link: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str
    family_id: str
    family_name: str | None = None
    protocol_scope: Literal["template", "concrete"] = "concrete"
    template_protocol_id: str | None = None
    template_protocol_name: str | None = None
    species: list[str] = Field(default_factory=list)
    curation_status: str
    stimulus: dict[str, Any]
    choice: dict[str, Any]
    timing: list[dict[str, Any]] = Field(default_factory=list)
    feedback: dict[str, Any]
    training: dict[str, Any]
    apparatus: list[str] = Field(default_factory=list)
    software: list[str] = Field(default_factory=list)
    expected_analyses: list[str] = Field(default_factory=list)
    interpretive_claims: list[dict[str, Any]] = Field(default_factory=list)
    datasets: list[CatalogLinkedDataset] = Field(default_factory=list)
    vertical_slices: list[CatalogLinkedSlice] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any]
    open_questions: list[str] = Field(default_factory=list)
    report_status: str


class CatalogDatasetRow(StrictModel):
    dataset_id: str
    detail_link: str
    name: str
    protocol_ids: list[str] = Field(default_factory=list)
    species: list[str] = Field(default_factory=list)
    source_url: str
    source_data_level: str
    license: str | None = None
    curation_status: str
    slice_ids: list[str] = Field(default_factory=list)


class CatalogDatasetDetail(StrictModel):
    dataset_id: str
    detail_link: str
    name: str
    description: str
    protocol_ids: list[str] = Field(default_factory=list)
    protocols: list[CatalogLinkedProtocol] = Field(default_factory=list)
    species: list[str] = Field(default_factory=list)
    curation_status: str
    source_url: str
    access_notes: str
    source_data_level: str
    license: str | None = None
    data_formats: list[str] = Field(default_factory=list)
    expected_trial_table_mapping: dict[str, str] = Field(default_factory=dict)
    vertical_slices: list[CatalogLinkedSlice] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any]
    caveats: list[str] = Field(default_factory=list)


class CatalogSliceRow(StrictModel):
    slice_id: str
    title: str
    family_id: str
    protocol_id: str
    dataset_id: str
    species: str
    modality: str
    stimulus_metric: str
    evidence_type: str
    source_data_level: str
    report_status: str
    artifact_status: str
    primary_link: str | None = None


class CatalogPayload(StrictModel):
    catalog_schema_version: str
    title: str
    generated_at: str
    behavtaskatlas_commit: str | None = None
    behavtaskatlas_git_dirty: bool | None = None
    derived_dir: str
    catalog_json_link: str
    report_index_link: str
    graph_link: str
    graph_json_link: str
    curation_queue_link: str
    health: dict[str, Any] = Field(default_factory=dict)
    counts: dict[str, int]
    task_families: list[CatalogFamilyRow]
    protocols: list[CatalogProtocolRow]
    protocol_details: list[CatalogProtocolDetail]
    datasets: list[CatalogDatasetRow]
    dataset_details: list[CatalogDatasetDetail]
    vertical_slices: list[CatalogSliceRow]


class RelationshipGraphNode(StrictModel):
    node_id: str
    node_type: str
    label: str
    href: str | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipGraphEdge(StrictModel):
    source: str
    target: str
    edge_type: str
    label: str


class RelationshipGraphIssue(StrictModel):
    issue_id: str
    severity: Literal["info", "warning", "error"]
    issue_type: str
    node_id: str | None = None
    related_node_id: str | None = None
    message: str


class RelationshipGraphPayload(StrictModel):
    graph_schema_version: str
    title: str
    generated_at: str
    behavtaskatlas_commit: str | None = None
    behavtaskatlas_git_dirty: bool | None = None
    catalog_link: str
    graph_json_link: str
    curation_queue_link: str
    counts: dict[str, int]
    qa_summary: dict[str, int]
    qa_issues: list[RelationshipGraphIssue] = Field(default_factory=list)
    nodes: list[RelationshipGraphNode]
    edges: list[RelationshipGraphEdge]


class CurationQueueItem(StrictModel):
    item_id: str
    action_type: str
    priority: Literal["low", "normal", "high"]
    status: Literal["open", "blocked", "done"] = "open"
    source_issue_id: str
    source_issue_type: str
    source_severity: Literal["info", "warning", "error"]
    node_id: str | None = None
    node_label: str | None = None
    node_type: str | None = None
    related_node_id: str | None = None
    message: str
    suggested_next_step: str
    href: str | None = None


class CurationQueuePayload(StrictModel):
    queue_schema_version: str
    title: str
    generated_at: str
    behavtaskatlas_commit: str | None = None
    behavtaskatlas_git_dirty: bool | None = None
    graph_link: str
    queue_json_link: str
    counts: dict[str, int]
    action_counts: dict[str, int]
    priority_counts: dict[str, int]
    items: list[CurationQueueItem]


class ReleaseCheckItem(StrictModel):
    check_id: str
    label: str
    status: Literal["ok", "warning", "error"]
    message: str
    path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ReleaseCheckPayload(StrictModel):
    release_check_schema_version: str
    title: str
    generated_at: str
    behavtaskatlas_commit: str | None = None
    behavtaskatlas_git_dirty: bool | None = None
    root: str
    derived_dir: str
    overall_status: Literal["ok", "warning", "error"]
    counts: dict[str, int] = Field(default_factory=dict)
    items: list[ReleaseCheckItem]


class Paper(StrictModel):
    object_type: Literal["paper"]
    schema_version: str
    id: str
    citation: str
    authors: list[str] = Field(default_factory=list)
    year: int
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    lab: str | None = None
    species: list[str]
    n_subjects: int | None = None
    protocol_ids: list[str]
    dataset_ids: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    curation_status: str
    notes: str | None = None
    provenance: Provenance


class CurvePoint(StrictModel):
    x: float
    n: int
    y: float
    y_lower: float | None = None
    y_upper: float | None = None
    se: float | None = None


class StratificationKey(StrictModel):
    species: str | None = None
    response_modality: str | None = None
    training_stage: str | None = None
    condition: str | None = None
    subject_id: str | None = None
    age_group: str | None = None


class ResultCurve(StrictModel):
    curve_type: Literal[
        "psychometric",
        "chronometric",
        "accuracy_by_strength",
        "hit_rate_by_condition",
        "rt_distribution",
    ]
    x_label: str
    x_units: str
    y_label: str
    points: list[CurvePoint]
    fit: dict[str, float] | None = None


class Finding(StrictModel):
    object_type: Literal["finding"]
    schema_version: str
    id: str
    paper_id: str
    protocol_id: str
    dataset_id: str | None = None
    slice_id: str | None = None
    source_data_level: str
    n_trials: int | None = None
    n_subjects: int | None = None
    stratification: StratificationKey
    curve: ResultCurve
    interpretation_claims: list[InterpretationClaim] = Field(default_factory=list)
    extraction_method: Literal[
        "harmonized-pipeline",
        "supplement-csv",
        "figure-trace",
        "table-transcription",
    ]
    extraction_notes: str | None = None
    provenance: Provenance


class FindingsIndexCurvePoint(StrictModel):
    x: float
    n: int
    y: float
    y_lower: float | None = None
    y_upper: float | None = None


class FindingsIndexEntry(StrictModel):
    finding_id: str
    paper_id: str
    paper_citation: str
    paper_year: int
    paper_lab: str | None = None
    paper_doi: str | None = None
    protocol_id: str
    protocol_name: str
    family_id: str
    family_name: str | None = None
    dataset_id: str | None = None
    slice_id: str | None = None
    species: str | None = None
    modalities: list[str] = Field(default_factory=list)
    evidence_type: str | None = None
    response_modality: str | None = None
    source_data_level: str
    extraction_method: str
    n_trials: int | None = None
    n_subjects: int | None = None
    stratification: StratificationKey
    curve_type: str
    x_label: str
    x_units: str
    y_label: str
    points: list[FindingsIndexCurvePoint]
    fit: dict[str, float] | None = None


class FindingsIndexPayload(StrictModel):
    findings_schema_version: str
    title: str
    generated_at: str
    behavtaskatlas_commit: str | None = None
    behavtaskatlas_git_dirty: bool | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    findings: list[FindingsIndexEntry]


class Comparison(StrictModel):
    object_type: Literal["comparison"]
    schema_version: str
    id: str
    title: str
    question: str
    framing: str
    finding_ids: list[str]
    color_by: Literal["paper", "condition", "curve_type"] = "paper"
    hint: str
    display_order: int = 100
    curation_status: str
    provenance: Provenance


class ComparisonsIndexEntry(StrictModel):
    id: str
    title: str
    question: str
    framing: str
    finding_ids: list[str]
    color_by: Literal["paper", "condition", "curve_type"]
    hint: str
    display_order: int


class ComparisonsIndexPayload(StrictModel):
    comparisons_schema_version: str
    title: str
    generated_at: str
    behavtaskatlas_commit: str | None = None
    behavtaskatlas_git_dirty: bool | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    comparisons: list[ComparisonsIndexEntry]


Record = (
    TaskFamily
    | Protocol
    | Dataset
    | Implementation
    | VerticalSlice
    | Paper
    | Finding
    | Comparison
)


MODEL_BY_OBJECT_TYPE: dict[str, type[BaseModel]] = {
    "task_family": TaskFamily,
    "protocol": Protocol,
    "dataset": Dataset,
    "implementation": Implementation,
    "vertical_slice": VerticalSlice,
    "paper": Paper,
    "finding": Finding,
    "comparison": Comparison,
}


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    **MODEL_BY_OBJECT_TYPE,
    "canonical_trial": CanonicalTrial,
    "report_manifest": ReportManifest,
    "catalog": CatalogPayload,
    "relationship_graph": RelationshipGraphPayload,
    "curation_queue": CurationQueuePayload,
    "release_check": ReleaseCheckPayload,
    "findings_index": FindingsIndexPayload,
    "comparisons_index": ComparisonsIndexPayload,
}


def model_from_record(data: dict[str, Any]) -> BaseModel:
    object_type = data.get("object_type")
    model = MODEL_BY_OBJECT_TYPE.get(object_type)
    if model is None:
        raise ValueError(f"Unknown object_type: {object_type!r}")
    return model.model_validate(data)
