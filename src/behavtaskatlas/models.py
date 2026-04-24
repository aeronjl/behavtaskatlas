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
    choice: Literal["left", "right", "no-response", "unknown"]
    correct: bool | None = None
    response_time: float | None = None
    response_time_origin: str | None = None
    feedback: Literal["reward", "error", "none", "unknown"] = "unknown"
    reward: float | None = None
    reward_units: str | None = None
    block_id: str | None = None
    prior_context: str | None = None
    training_stage: str | None = None
    source: dict[str, Any] = Field(default_factory=dict)


Record = TaskFamily | Protocol | Dataset | Implementation


MODEL_BY_OBJECT_TYPE: dict[str, type[BaseModel]] = {
    "task_family": TaskFamily,
    "protocol": Protocol,
    "dataset": Dataset,
    "implementation": Implementation,
}


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    **MODEL_BY_OBJECT_TYPE,
    "canonical_trial": CanonicalTrial,
}


def model_from_record(data: dict[str, Any]) -> BaseModel:
    object_type = data.get("object_type")
    model = MODEL_BY_OBJECT_TYPE.get(object_type)
    if model is None:
        raise ValueError(f"Unknown object_type: {object_type!r}")
    return model.model_validate(data)
