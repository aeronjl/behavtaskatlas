"""Render Paper records as BibTeX and RIS bibliography entries."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from behavtaskatlas.models import Dataset, Finding, Paper, Protocol, VerticalSlice


def _bib_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _ascii_slug(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", ascii_only)
    return cleaned


def _bib_key(paper: Paper) -> str:
    if paper.authors:
        first_surname = paper.authors[0].split(",", 1)[0].strip()
        return f"{_ascii_slug(first_surname)}{paper.year}"
    fallback = paper.id.split(".", 1)[-1]
    return _ascii_slug(fallback) or f"paper{paper.year}"


def _bib_authors(authors: Iterable[str]) -> str:
    names: list[str] = []
    for author in authors:
        if "," in author:
            surname, given = (part.strip() for part in author.split(",", 1))
            names.append(f"{surname}, {given}")
        else:
            names.append(author.strip())
    return " and ".join(names)


def _short_title(paper: Paper) -> str:
    citation = re.sub(r"\s+", " ", paper.citation.strip())
    tail = citation
    if paper.authors:
        last_author_surname = paper.authors[-1].split(",", 1)[0].strip()
        idx = citation.find(last_author_surname)
        if idx >= 0:
            after_authors = citation[idx + len(last_author_surname) :]
            # Authors block typically ends with ". " (after trailing initials).
            # Title is the next sentence ending in ". ".
            sep = re.search(r"\.\s+", after_authors)
            if sep is not None:
                tail = after_authors[sep.end() :]
            else:
                tail = after_authors.lstrip(" .,")
    venue = paper.venue or ""
    if venue:
        venue_idx = tail.find(venue)
        if venue_idx >= 0:
            tail = tail[:venue_idx]
    tail = tail.strip().rstrip(".,;: ")
    return tail or paper.citation.strip().rstrip(".")


def render_bibtex_entry(paper: Paper) -> str:
    fields: list[tuple[str, str]] = []
    if paper.authors:
        fields.append(("author", _bib_authors(paper.authors)))
    title = _short_title(paper)
    if title:
        fields.append(("title", title))
    if paper.venue:
        fields.append(("journal", paper.venue))
    fields.append(("year", str(paper.year)))
    if paper.doi:
        fields.append(("doi", paper.doi))
    if paper.url:
        fields.append(("url", paper.url))

    lines = [f"@article{{{_bib_key(paper)},"]
    for i, (key, value) in enumerate(fields):
        comma = "," if i < len(fields) - 1 else ""
        lines.append(f"  {key} = {{{_bib_escape(value)}}}{comma}")
    lines.append("}")
    return "\n".join(lines)


def render_bibtex(papers: Iterable[Paper]) -> str:
    entries = [render_bibtex_entry(p) for p in papers]
    return "\n\n".join(entries) + "\n"


def render_ris_entry(paper: Paper) -> str:
    lines: list[str] = ["TY  - JOUR"]
    title = _short_title(paper)
    if title:
        lines.append(f"TI  - {title}")
    for author in paper.authors:
        if "," in author:
            surname, given = (part.strip() for part in author.split(",", 1))
            lines.append(f"AU  - {surname}, {given}")
        else:
            lines.append(f"AU  - {author.strip()}")
    lines.append(f"PY  - {paper.year}")
    if paper.venue:
        lines.append(f"JO  - {paper.venue}")
    if paper.doi:
        lines.append(f"DO  - {paper.doi}")
    if paper.url:
        lines.append(f"UR  - {paper.url}")
    lines.append("ER  - ")
    return "\n".join(lines)


def render_ris(papers: Iterable[Paper]) -> str:
    entries = [render_ris_entry(p) for p in papers]
    return "\n\n".join(entries) + "\n"


def slug_for_paper_id(paper_id: str) -> str:
    return paper_id.split(".", 1)[-1] if "." in paper_id else paper_id


def write_citation_files(papers: list[Paper], out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sorted_papers = sorted(papers, key=lambda p: (p.year, p.id))
    (out_dir / "atlas.bib").write_text(render_bibtex(sorted_papers), encoding="utf-8")
    (out_dir / "atlas.ris").write_text(render_ris(sorted_papers), encoding="utf-8")
    for paper in sorted_papers:
        slug = slug_for_paper_id(paper.id)
        (out_dir / f"{slug}.bib").write_text(
            render_bibtex_entry(paper) + "\n", encoding="utf-8"
        )
        (out_dir / f"{slug}.ris").write_text(
            render_ris_entry(paper) + "\n", encoding="utf-8"
        )
    return {"papers": len(sorted_papers), "files": 2 + 2 * len(sorted_papers)}


def _sorted_unique(values: Iterable[str | None]) -> list[str]:
    return sorted({value for value in values if value})


def _paper_coverage_status(
    *,
    finding_count: int,
    slice_ids: list[str],
    dataset_ids: list[str],
    protocol_ids: list[str],
) -> str:
    if finding_count > 0:
        return "findings"
    if slice_ids:
        return "analysis-linked"
    if dataset_ids:
        return "data-linked"
    if protocol_ids:
        return "protocol-linked"
    return "bibliography-only"


def build_papers_index(
    papers: list[Paper],
    *,
    findings: Iterable[Finding] | None = None,
    protocols: Iterable[Protocol] | None = None,
    datasets: Iterable[Dataset] | None = None,
    slices: Iterable[VerticalSlice] | None = None,
) -> dict[str, object]:
    sorted_papers = sorted(papers, key=lambda p: (p.year, p.id))
    linked_findings_by_paper: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings or ():
        linked_findings_by_paper[finding.paper_id].append(finding)

    protocol_by_id = {p.id: p for p in protocols or ()}
    dataset_by_id = {d.id: d for d in datasets or ()}
    slice_by_id = {s.id: s for s in slices or ()}

    paper_entries: list[dict[str, Any]] = []
    for paper in sorted_papers:
        linked_findings = sorted(
            linked_findings_by_paper.get(paper.id, []),
            key=lambda finding: finding.id,
        )
        protocol_ids = _sorted_unique(
            [
                *paper.protocol_ids,
                *(finding.protocol_id for finding in linked_findings),
            ]
        )
        dataset_ids = _sorted_unique(
            [
                *paper.dataset_ids,
                *(finding.dataset_id for finding in linked_findings),
            ]
        )
        finding_ids = _sorted_unique(
            [
                *paper.finding_ids,
                *(finding.id for finding in linked_findings),
            ]
        )
        finding_slice_ids = _sorted_unique(
            finding.slice_id for finding in linked_findings
        )
        slice_ids = _sorted_unique(
            [
                *finding_slice_ids,
                *(
                    slice_record.id
                    for slice_record in slice_by_id.values()
                    if slice_record.dataset_id in set(dataset_ids)
                ),
            ]
        )
        source_data_levels = _sorted_unique(
            [
                *(finding.source_data_level for finding in linked_findings),
                *(
                    dataset_by_id[dataset_id].source_data_level
                    for dataset_id in dataset_ids
                    if dataset_id in dataset_by_id
                ),
                *(
                    slice_by_id[slice_id].comparison.source_data_level
                    for slice_id in slice_ids
                    if slice_id in slice_by_id
                ),
            ]
        )
        curve_types = _sorted_unique(
            finding.curve.curve_type for finding in linked_findings
        )
        total_n_trials = sum(
            finding.n_trials for finding in linked_findings if finding.n_trials
        )
        finding_n_subjects = [
            finding.n_subjects for finding in linked_findings if finding.n_subjects
        ]
        finding_n_subjects_max = max(finding_n_subjects, default=None)

        paper_entries.append(
            {
                "id": paper.id,
                "slug": slug_for_paper_id(paper.id),
                "citation": paper.citation.strip(),
                "authors": list(paper.authors),
                "year": paper.year,
                "venue": paper.venue,
                "doi": paper.doi,
                "url": paper.url,
                "lab": paper.lab,
                "species": list(paper.species),
                "n_subjects": paper.n_subjects,
                "protocol_ids": protocol_ids,
                "dataset_ids": dataset_ids,
                "finding_ids": finding_ids,
                "slice_ids": slice_ids,
                "curation_status": paper.curation_status,
                "coverage_status": _paper_coverage_status(
                    finding_count=len(linked_findings),
                    slice_ids=slice_ids,
                    dataset_ids=dataset_ids,
                    protocol_ids=protocol_ids,
                ),
                "has_findings": bool(linked_findings),
                "finding_count": len(linked_findings),
                "curve_types": curve_types,
                "source_data_levels": source_data_levels,
                "total_n_trials": total_n_trials,
                "finding_n_subjects_max": finding_n_subjects_max,
                "protocols": [
                    {
                        "protocol_id": protocol_id,
                        "name": protocol_by_id[protocol_id].name
                        if protocol_id in protocol_by_id
                        else protocol_id,
                    }
                    for protocol_id in protocol_ids
                ],
                "datasets": [
                    {
                        "dataset_id": dataset_id,
                        "name": dataset_by_id[dataset_id].name
                        if dataset_id in dataset_by_id
                        else dataset_id,
                        "source_data_level": dataset_by_id[
                            dataset_id
                        ].source_data_level
                        if dataset_id in dataset_by_id
                        else None,
                    }
                    for dataset_id in dataset_ids
                ],
                "vertical_slices": [
                    {
                        "slice_id": slice_id,
                        "title": slice_by_id[slice_id].title
                        if slice_id in slice_by_id
                        else slice_id,
                        "source_data_level": slice_by_id[
                            slice_id
                        ].comparison.source_data_level
                        if slice_id in slice_by_id
                        else None,
                    }
                    for slice_id in slice_ids
                ],
                "notes": paper.notes,
                "bibtex": render_bibtex_entry(paper),
                "ris": render_ris_entry(paper),
            }
        )

    return {
        "counts": {"papers": len(sorted_papers)},
        "atlas_bibtex": render_bibtex(sorted_papers),
        "atlas_ris": render_ris(sorted_papers),
        "papers": paper_entries,
    }
