"""Render Paper records as BibTeX and RIS bibliography entries."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path

from behavtaskatlas.models import Paper


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


def build_papers_index(papers: list[Paper]) -> dict[str, object]:
    sorted_papers = sorted(papers, key=lambda p: (p.year, p.id))
    return {
        "counts": {"papers": len(sorted_papers)},
        "atlas_bibtex": render_bibtex(sorted_papers),
        "atlas_ris": render_ris(sorted_papers),
        "papers": [
            {
                "id": p.id,
                "slug": slug_for_paper_id(p.id),
                "citation": p.citation.strip(),
                "authors": list(p.authors),
                "year": p.year,
                "venue": p.venue,
                "doi": p.doi,
                "url": p.url,
                "lab": p.lab,
                "species": list(p.species),
                "n_subjects": p.n_subjects,
                "bibtex": render_bibtex_entry(p),
                "ris": render_ris_entry(p),
            }
            for p in sorted_papers
        ],
    }
