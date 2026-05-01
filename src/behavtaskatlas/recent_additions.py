"""Recent additions feed for the landing page.

Surfaces the N most recently added findings, papers, and slices so a
first-time visitor sees that the atlas is alive without having to
return for the WhatsChangedBanner to fire. Recency is sourced from
``git log --diff-filter=A`` so the date reflects when the YAML record
landed in the repo, not the paper's publication year or a checkout
mtime.

A single ``git log`` invocation handles all three record types so the
build cost is one subprocess, not one per file. Records that are not
under git (e.g. a freshly-staged add that was never committed) fall
through silently — the feed just shows older entries.

The function consumes the already-denormalized index entries from
``build_findings_index`` and ``build_papers_index`` so it doesn't have
to re-cross-reference paper citations, species, family ids, etc. The
slice list is taken raw because the catalog payload's slice rows
don't carry the source-data-level we want to surface.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from behavtaskatlas.models import VerticalSlice


def _git_added_dates(repo_root: Path, paths: Iterable[str]) -> dict[str, str]:
    """Return ``{path: YYYY-MM-DD}`` for each path's add commit.

    Uses ``--diff-filter=A --reverse`` so the first occurrence we see for
    a path is its add commit. Paths not under git get omitted.
    """
    paths = list(paths)
    if not paths:
        return {}
    cmd = [
        "git",
        "log",
        "--diff-filter=A",
        "--name-only",
        "--reverse",
        "--format=COMMIT %cs",
        "--",
        *paths,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {}

    added: dict[str, str] = {}
    current_date: str | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("COMMIT "):
            current_date = line[7:].strip() or None
            continue
        if not line.strip() or current_date is None:
            continue
        if line not in added:
            added[line] = current_date
    return added


def _slug_for_id(record_id: str) -> str:
    return record_id.split(".", 1)[1] if "." in record_id else record_id


def _finding_path(finding_id: str) -> str:
    return f"findings/{finding_id.removeprefix('finding.')}.yaml"


def _paper_path(paper_id: str) -> str:
    return f"papers/{paper_id.removeprefix('paper.')}.yaml"


def _slice_path(slice_id: str) -> str:
    # Slice records use `slice.<slug>` ids with hyphenated slugs, but the
    # on-disk directory uses underscores (e.g. `auditory_clicks`). Mirror
    # that here so git log finds the file.
    bare = slice_id.removeprefix("slice.").removeprefix("vertical_slice.")
    return f"vertical_slices/{bare.replace('-', '_')}/slice.yaml"


def build_recent_additions_payload(
    *,
    repo_root: Path,
    findings_index: list[dict[str, Any]],
    papers_index: list[dict[str, Any]],
    slices: list[VerticalSlice],
    limit: int = 12,
) -> dict[str, Any]:
    """Build a denormalized recent-additions feed for the homepage.

    The feed is a flat list of records sorted by ``added_at`` descending.
    Each item carries enough fields to render a card without re-loading
    the source records on the frontend: kind, id, slug, title, a short
    secondary line, href, and added_at. Family-id is also exposed per
    item so the landing page can pick a story tied to a recently-active
    family without having to re-cross-reference.
    """
    paths_to_record: dict[str, tuple[str, dict[str, Any]]] = {}

    for finding in findings_index:
        finding_id = finding.get("finding_id")
        if not finding_id:
            continue
        title_source = finding.get("paper_citation") or finding_id
        title = title_source.split(".")[0] if isinstance(title_source, str) else str(finding_id)
        secondary_bits = [
            str(finding[k])
            for k in ("species", "curve_type")
            if finding.get(k)
        ]
        paths_to_record[_finding_path(finding_id)] = (
            "finding",
            {
                "id": finding_id,
                "slug": _slug_for_id(finding_id),
                "title": title,
                "secondary": " · ".join(secondary_bits),
                "href": f"/findings/{_slug_for_id(finding_id)}",
                "family_id": finding.get("family_id"),
                "species": finding.get("species"),
            },
        )

    for paper in papers_index:
        paper_id = paper.get("id")
        if not paper_id:
            continue
        citation = paper.get("citation") or ""
        title = citation.split(".")[0] if citation else paper_id
        secondary_bits: list[str] = []
        if paper.get("year"):
            secondary_bits.append(str(paper["year"]))
        if paper.get("venue"):
            secondary_bits.append(str(paper["venue"]))
        paths_to_record[_paper_path(paper_id)] = (
            "paper",
            {
                "id": paper_id,
                "slug": paper.get("slug") or _slug_for_id(paper_id),
                "title": title,
                "secondary": " · ".join(secondary_bits),
                "href": f"/papers/{paper.get('slug') or _slug_for_id(paper_id)}",
                "family_id": None,
                "species": None,
            },
        )

    for slice_record in slices:
        slice_id = slice_record.id
        family_id = getattr(slice_record, "family_id", None)
        secondary_bits: list[str] = []
        if family_id:
            family_label = (
                family_id.removeprefix("task_family.")
                .removeprefix("family.")
                .replace("_", " ")
                .replace("-", " ")
            )
            secondary_bits.append(family_label)
        paths_to_record[_slice_path(slice_id)] = (
            "slice",
            {
                "id": slice_id,
                "slug": _slug_for_id(slice_id),
                "title": slice_record.title or _slug_for_id(slice_id),
                "secondary": " · ".join(secondary_bits),
                "href": f"/slices/{_slug_for_id(slice_id)}",
                "family_id": family_id,
                "species": None,
            },
        )

    added_dates = _git_added_dates(repo_root, paths_to_record.keys())

    items: list[dict[str, Any]] = []
    for path, (kind, payload) in paths_to_record.items():
        added_at = added_dates.get(path)
        if not added_at:
            continue
        items.append({"kind": kind, "added_at": added_at, **payload})

    items.sort(key=lambda row: (row["added_at"], row["id"]), reverse=True)

    family_last_added: dict[str, str] = {}
    for row in items:
        fid = row.get("family_id")
        if not fid:
            continue
        if fid not in family_last_added or row["added_at"] > family_last_added[fid]:
            family_last_added[fid] = row["added_at"]

    return {
        "items": items[:limit],
        "family_last_added": family_last_added,
        "counts": {
            "total": len(items),
            "findings": sum(1 for r in items if r["kind"] == "finding"),
            "papers": sum(1 for r in items if r["kind"] == "paper"),
            "slices": sum(1 for r in items if r["kind"] == "slice"),
        },
        "as_of": date.today().isoformat(),
    }
