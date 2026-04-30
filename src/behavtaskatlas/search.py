"""Build a flat search index across every record type in the atlas."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from behavtaskatlas.citations import slug_for_paper_id
from behavtaskatlas.data_requests import data_request_export_path
from behavtaskatlas.models import (
    Comparison,
    DataRequest,
    Dataset,
    Finding,
    ModelFamily,
    ModelVariant,
    Paper,
    Protocol,
    TaskFamily,
    VerticalSlice,
)

DEFAULT_STORIES: tuple[dict[str, Any], ...] = (
    {
        "id": "story.index",
        "title": "Stories",
        "subtitle": "Curated synthesis views across findings, fits, and slices",
        "body": (
            "Long-form views that follow a question across the atlas on shared "
            "canonical axes."
        ),
        "href": "/stories",
        "keywords": ["story", "stories", "synthesis", "models", "findings"],
    },
    {
        "id": "story.visual-contrast",
        "title": "Visual contrast family map",
        "subtitle": "Timeline, coverage matrix, small multiples, and model ambiguity",
        "body": (
            "Visual contrast discrimination coverage across notable papers, "
            "protocol variants, source-data levels, extracted findings, slices, "
            "small-multiple curve galleries, and model-selection winners."
        ),
        "href": "/stories/visual-contrast",
        "keywords": [
            "story",
            "visual contrast",
            "2afc",
            "psychometric",
            "small multiples",
            "curve gallery",
            "coverage",
            "family depth",
            "model selection",
        ],
    },
    {
        "id": "story.rdm",
        "title": "Cross-species random-dot motion",
        "subtitle": "Psychometric + chronometric + DDM cross-species fits",
        "body": (
            "Classic macaque RDM, human reaction-time RDM, and macaque "
            "confidence-wagering RDM live on one canonical signed-coherence axis."
        ),
        "href": "/stories/rdm",
        "keywords": [
            "story",
            "random-dot motion",
            "rdm",
            "ddm",
            "drift diffusion",
            "cross-species",
        ],
    },
    {
        "id": "story.prior-shifts",
        "title": "Prior conditioning shifts the psychometric, not the slope",
        "subtitle": "Psychometric mu vs sigma across mouse blocks and human cues",
        "body": (
            "IBL left-prior blocks and Walsh human valid-neutral-invalid cues "
            "both predict psychometric location shifts with slope preserved."
        ),
        "href": "/stories/prior-shifts",
        "keywords": [
            "story",
            "prior conditioning",
            "psychometric",
            "walsh",
            "ibl",
            "cross-species",
        ],
    },
)


def _slug(record_id: str) -> str:
    return record_id.split(".", 1)[-1] if "." in record_id else record_id


def _join(parts: Iterable[str | None]) -> str:
    return " · ".join(p for p in parts if p)


def _entry(
    *,
    id: str,
    type: str,
    title: str,
    subtitle: str | None,
    body: str | None,
    href: str,
    keywords: Iterable[str | None] = (),
) -> dict[str, Any]:
    keyword_list = sorted({k.strip() for k in keywords if k and k.strip()})
    return {
        "id": id,
        "type": type,
        "title": title,
        "subtitle": subtitle or "",
        "body": (body or "").strip(),
        "href": href,
        "keywords": keyword_list,
    }


def _paper_entries(papers: list[Paper]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in papers:
        out.append(
            _entry(
                id=p.id,
                type="paper",
                title=p.citation.strip(),
                subtitle=_join([p.lab, str(p.year), p.venue]),
                body=p.notes,
                href=f"/papers/{slug_for_paper_id(p.id)}",
                keywords=[*p.authors, p.venue, p.doi, *(p.species or [])],
            )
        )
    return out


def _family_entries(families: list[TaskFamily]) -> list[dict[str, Any]]:
    return [
        _entry(
            id=f.id,
            type="task_family",
            title=f.name,
            subtitle=_join([", ".join(f.modalities), ", ".join(f.common_choice_types)]),
            body=f.description,
            href=f"/catalog#{_slug(f.id)}",
            keywords=[*f.aliases, *f.modalities, *f.canonical_variables],
        )
        for f in families
    ]


def _protocol_entries(protocols: list[Protocol]) -> list[dict[str, Any]]:
    return [
        _entry(
            id=p.id,
            type="protocol",
            title=p.name,
            subtitle=_join(
                [
                    p.family_id,
                    ", ".join(p.species),
                    p.choice.choice_type,
                    ", ".join(p.stimulus.modalities or []),
                ]
            ),
            body=p.description,
            href=f"/protocols/{_slug(p.id)}",
            keywords=[
                *p.aliases,
                *p.species,
                *p.apparatus,
                *p.software,
                *(p.stimulus.modalities or []),
                p.choice.choice_type,
            ],
        )
        for p in protocols
    ]


def _dataset_entries(datasets: list[Dataset]) -> list[dict[str, Any]]:
    return [
        _entry(
            id=d.id,
            type="dataset",
            title=d.name,
            subtitle=_join([d.source_data_level, ", ".join(d.species), d.license]),
            body=d.description,
            href=f"/datasets/{_slug(d.id)}",
            keywords=[
                *d.species,
                *d.data_formats,
                d.source_url,
                d.source_data_level,
                d.license,
            ],
        )
        for d in datasets
    ]


def _slice_entries(slices: list[VerticalSlice]) -> list[dict[str, Any]]:
    return [
        _entry(
            id=s.id,
            type="vertical_slice",
            title=s.title,
            subtitle=_join(
                [
                    s.comparison.species,
                    s.comparison.modality,
                    s.comparison.choice_type,
                    s.comparison.source_data_level,
                ]
            ),
            body=s.description,
            href=f"/slices/{_slug(s.id)}",
            keywords=[
                s.comparison.species,
                s.comparison.modality,
                s.comparison.evidence_type,
                s.comparison.response_modality,
                s.comparison.source_data_level,
                s.family_id,
                s.protocol_id,
                s.dataset_id,
            ],
        )
        for s in slices
    ]


def _finding_entries(
    findings: list[Finding], paper_lookup: dict[str, Paper]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in findings:
        paper = paper_lookup.get(f.paper_id)
        paper_title = paper.citation.strip() if paper else f.paper_id
        strat = f.stratification
        strat_bits = [
            strat.species,
            strat.subject_id,
            strat.condition,
            strat.training_stage,
            strat.response_modality,
            strat.age_group,
        ]
        title = f"{f.curve.curve_type} · {paper_title}"
        out.append(
            _entry(
                id=f.id,
                type="finding",
                title=title,
                subtitle=_join(
                    [
                        f.source_data_level,
                        strat.subject_id,
                        strat.condition,
                    ]
                ),
                body=f.extraction_notes,
                href=f"/findings/{_slug(f.id)}",
                keywords=[
                    f.curve.curve_type,
                    f.curve.x_label,
                    f.protocol_id,
                    f.dataset_id,
                    f.slice_id,
                    *strat_bits,
                ],
            )
        )
    return out


def _comparison_entries(comparisons: list[Comparison]) -> list[dict[str, Any]]:
    return [
        _entry(
            id=c.id,
            type="comparison",
            title=c.title,
            subtitle=c.question,
            body=_join([c.framing, c.hint]),
            href=f"/compare#{_slug(c.id)}",
            keywords=[c.color_by, *c.finding_ids],
        )
        for c in comparisons
    ]


def _model_entries(
    families: list[ModelFamily], variants: list[ModelVariant]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    families_by_id = {family.id: family for family in families}
    variants_by_family: dict[str, list[ModelVariant]] = {}
    for variant in variants:
        variants_by_family.setdefault(variant.family_id, []).append(variant)

    for family in families:
        family_variants = variants_by_family.get(family.id, [])
        out.append(
            _entry(
                id=family.id,
                type="model",
                title=f"{family.name} model family",
                subtitle=_join(
                    [
                        "model family",
                        ", ".join(family.applicable_curve_types),
                        f"{len(family_variants)} variants",
                    ]
                ),
                body=_join([family.description, family.notes]),
                href=f"/models#{_slug(family.id)}",
                keywords=[
                    family.id,
                    family.name,
                    "model",
                    "model family",
                    *family.applicable_curve_types,
                    *family.requires,
                    *[
                        token
                        for parameter in family.parameter_definitions
                        for token in (
                            parameter.name,
                            parameter.symbol,
                            parameter.units,
                            parameter.description,
                        )
                    ],
                ],
            )
        )

    for variant in variants:
        family = families_by_id.get(variant.family_id)
        out.append(
            _entry(
                id=variant.id,
                type="model",
                title=f"{variant.name} model variant",
                subtitle=_join(
                    [
                        family.name if family else variant.family_id,
                        f"free: {', '.join(variant.free_parameters)}"
                        if variant.free_parameters
                        else None,
                    ]
                ),
                body=_join([variant.description, variant.notes]),
                href=f"/models#{_slug(variant.id)}",
                keywords=[
                    variant.id,
                    variant.family_id,
                    family.name if family else None,
                    "model",
                    "model variant",
                    *variant.free_parameters,
                    *variant.fixed_parameters.keys(),
                    *variant.requires,
                    *[
                        token
                        for parameter in variant.additional_parameters
                        for token in (
                            parameter.name,
                            parameter.symbol,
                            parameter.units,
                            parameter.description,
                        )
                    ],
                ],
            )
        )
    return out


def _data_request_entries(data_requests: list[DataRequest]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for request in data_requests:
        out.append(
            _entry(
                id=request.id,
                type="data_request",
                title=request.title,
                subtitle=_join(
                    [
                        request.status.replace("_", " "),
                        request.priority,
                        request.request_type.replace("_", " "),
                        request.blocker_type,
                    ]
                ),
                body=_join(
                    [
                        request.purpose,
                        request.blocker_detail,
                        request.next_action,
                        request.notes,
                    ]
                ),
                href=data_request_export_path(request.id),
                keywords=[
                    request.id,
                    request.status,
                    request.priority,
                    request.request_type,
                    request.blocker_type,
                    *request.paper_ids,
                    *request.protocol_ids,
                    *request.dataset_ids,
                    *request.slice_ids,
                    *request.finding_ids,
                    *request.model_roadmap_issue_types,
                    *[
                        token
                        for requested_file in request.requested_files
                        for token in (
                            requested_file.name,
                            requested_file.description,
                            requested_file.evidence,
                        )
                    ],
                    *[
                        token
                        for evidence in request.evidence
                        for token in (
                            evidence.evidence_type,
                            evidence.description,
                            evidence.url,
                            evidence.path,
                        )
                    ],
                ],
            )
        )
    return out


def _story_entries(stories: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _entry(
            id=story["id"],
            type="story",
            title=story["title"],
            subtitle=story.get("subtitle"),
            body=story.get("body"),
            href=story["href"],
            keywords=story.get("keywords", []),
        )
        for story in stories
    ]


def build_search_index(
    *,
    papers: list[Paper],
    families: list[TaskFamily],
    protocols: list[Protocol],
    datasets: list[Dataset],
    slices: list[VerticalSlice],
    findings: list[Finding],
    comparisons: list[Comparison],
    model_families: list[ModelFamily] | None = None,
    model_variants: list[ModelVariant] | None = None,
    data_requests: list[DataRequest] | None = None,
    stories: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    paper_lookup = {p.id: p for p in papers}
    entries: list[dict[str, Any]] = []
    entries.extend(_paper_entries(papers))
    entries.extend(_family_entries(families))
    entries.extend(_protocol_entries(protocols))
    entries.extend(_dataset_entries(datasets))
    entries.extend(_slice_entries(slices))
    entries.extend(_finding_entries(findings, paper_lookup))
    entries.extend(_comparison_entries(comparisons))
    entries.extend(_model_entries(model_families or [], model_variants or []))
    entries.extend(_data_request_entries(data_requests or []))
    entries.extend(_story_entries(DEFAULT_STORIES if stories is None else stories))
    entries.sort(key=lambda e: (e["type"], e["title"]))
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["type"]] = counts.get(entry["type"], 0) + 1
    counts["total"] = len(entries)
    return {
        "counts": counts,
        "entries": entries,
    }
