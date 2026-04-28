"""Build a flat search index across every record type in the atlas."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from behavtaskatlas.citations import slug_for_paper_id
from behavtaskatlas.models import (
    Comparison,
    Dataset,
    Finding,
    Paper,
    Protocol,
    TaskFamily,
    VerticalSlice,
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
                href=f"/papers/{slug_for_paper_id(f.paper_id)}",
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


def build_search_index(
    *,
    papers: list[Paper],
    families: list[TaskFamily],
    protocols: list[Protocol],
    datasets: list[Dataset],
    slices: list[VerticalSlice],
    findings: list[Finding],
    comparisons: list[Comparison],
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
    entries.sort(key=lambda e: (e["type"], e["title"]))
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["type"]] = counts.get(entry["type"], 0) + 1
    counts["total"] = len(entries)
    return {
        "counts": counts,
        "entries": entries,
    }
