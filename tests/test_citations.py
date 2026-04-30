"""Tests for the BibTeX/RIS rendering of Paper records."""

from __future__ import annotations

from datetime import date

import pytest

from behavtaskatlas.citations import (
    build_papers_index,
    render_bibtex,
    render_bibtex_entry,
    render_ris,
    render_ris_entry,
    slug_for_paper_id,
)
from behavtaskatlas.models import (
    CurvePoint,
    Finding,
    Paper,
    Provenance,
    ResultCurve,
    StratificationKey,
)


def _make_paper(**overrides) -> Paper:
    base = {
        "object_type": "paper",
        "schema_version": "0.1.0",
        "id": "paper.roitman-shadlen-2002",
        "citation": (
            "Roitman JD, Shadlen MN. Response of neurons in the lateral "
            "intraparietal area during a combined visual discrimination "
            "reaction time task. Journal of Neuroscience, 2002, 22(21):9475-9489."
        ),
        "authors": ["Roitman, Jamie D.", "Shadlen, Michael N."],
        "year": 2002,
        "venue": "Journal of Neuroscience",
        "doi": "10.1523/JNEUROSCI.22-21-09475.2002",
        "url": "https://www.jneurosci.org/content/22/21/9475",
        "lab": "Shadlen",
        "species": ["non-human-primate"],
        "n_subjects": 2,
        "protocol_ids": ["protocol.x"],
        "dataset_ids": [],
        "finding_ids": [],
        "curation_status": "data-linked",
        "notes": None,
        "provenance": Provenance(
            curators=["behavtaskatlas"],
            created=date(2026, 4, 28),
            updated=date(2026, 4, 28),
        ),
    }
    base.update(overrides)
    return Paper(**base)


def _make_finding(**overrides) -> Finding:
    base = {
        "object_type": "finding",
        "schema_version": "0.1.0",
        "id": "finding.roitman-shadlen-2002.psychometric",
        "paper_id": "paper.roitman-shadlen-2002",
        "protocol_id": "protocol.x",
        "dataset_id": "dataset.x",
        "slice_id": "slice.x",
        "source_data_level": "processed-trial",
        "n_trials": 1200,
        "n_subjects": 2,
        "stratification": StratificationKey(species="non-human-primate"),
        "curve": ResultCurve(
            curve_type="psychometric",
            x_label="Signed coherence",
            x_units="percent",
            y_label="p_right",
            points=[
                CurvePoint(x=-50.0, n=100, y=0.05),
                CurvePoint(x=0.0, n=100, y=0.5),
                CurvePoint(x=50.0, n=100, y=0.95),
            ],
        ),
        "extraction_method": "harmonized-pipeline",
        "provenance": Provenance(
            curators=["behavtaskatlas"],
            created=date(2026, 4, 28),
            updated=date(2026, 4, 28),
        ),
    }
    base.update(overrides)
    return Finding(**base)


def test_bibtex_entry_strips_authors_from_title() -> None:
    paper = _make_paper()
    entry = render_bibtex_entry(paper)
    assert entry.startswith("@article{Roitman2002,")
    assert (
        "title = {Response of neurons in the lateral intraparietal area "
        "during a combined visual discrimination reaction time task}"
    ) in entry
    assert "author = {Roitman, Jamie D. and Shadlen, Michael N.}" in entry
    assert "journal = {Journal of Neuroscience}" in entry
    assert "year = {2002}" in entry
    assert "doi = {10.1523/JNEUROSCI.22-21-09475.2002}" in entry


def test_bibtex_entry_handles_single_author_and_strips_initials() -> None:
    paper = _make_paper(
        id="paper.london-2018",
        citation=(
            "London D. Poisson Clicks Task, DBS OFF/ON. Mendeley Data, 2018."
        ),
        authors=["London, Dennis"],
        year=2018,
        venue="Mendeley Data",
        doi=None,
        url=None,
    )
    entry = render_bibtex_entry(paper)
    assert "@article{London2018,\n" in entry
    assert "title = {Poisson Clicks Task, DBS OFF/ON}" in entry
    assert "doi" not in entry
    assert "url" not in entry


def test_bibtex_entry_fallbacks_to_id_when_no_authors() -> None:
    paper = _make_paper(
        id="paper.consortium-2021",
        citation="Some Consortium. A title. Venue, 2021.",
        authors=[],
        year=2021,
    )
    entry = render_bibtex_entry(paper)
    assert "@article{consortium2021," in entry


def test_bibtex_escapes_braces() -> None:
    paper = _make_paper(citation="X. {foo} bar. V, 2002.", authors=["X, Y"])
    entry = render_bibtex_entry(paper)
    assert "\\{foo\\}" in entry or "{foo}" not in entry.split("title = ", 1)[1]


def test_render_bibtex_separates_with_blank_line() -> None:
    p1 = _make_paper()
    p2 = _make_paper(
        id="paper.london-2018",
        citation="London D. T. V, 2018.",
        authors=["London, Dennis"],
        year=2018,
    )
    out = render_bibtex([p1, p2])
    assert out.count("@article{") == 2
    assert "}\n\n@article" in out


def test_ris_entry_emits_required_tags() -> None:
    paper = _make_paper()
    entry = render_ris_entry(paper)
    lines = entry.splitlines()
    assert lines[0] == "TY  - JOUR"
    assert lines[-1] == "ER  - "
    assert "AU  - Roitman, Jamie D." in entry
    assert "AU  - Shadlen, Michael N." in entry
    assert "PY  - 2002" in entry
    assert "JO  - Journal of Neuroscience" in entry
    assert "DO  - 10.1523/JNEUROSCI.22-21-09475.2002" in entry


def test_render_ris_concatenates_entries() -> None:
    p1 = _make_paper()
    p2 = _make_paper(
        id="paper.london-2018",
        citation="London D. Title. V, 2018.",
        authors=["London, Dennis"],
        year=2018,
    )
    out = render_ris([p1, p2])
    assert out.count("TY  - JOUR") == 2
    assert out.count("ER  - ") == 2


def test_build_papers_index_is_sorted_and_includes_strings() -> None:
    p_old = _make_paper()
    p_new = _make_paper(
        id="paper.walsh-2024",
        citation="Walsh K. Some title. eLife, 2024.",
        authors=["Walsh, Kevin"],
        year=2024,
        venue="eLife",
    )
    index = build_papers_index([p_new, p_old])
    assert index["counts"] == {"papers": 2}
    assert [p["id"] for p in index["papers"]] == [p_old.id, p_new.id]
    assert index["papers"][0]["bibtex"].startswith("@article{Roitman2002,")
    assert "TY  - JOUR" in index["papers"][0]["ris"]
    assert "@article{Walsh2024," in index["atlas_bibtex"]
    assert index["atlas_ris"].count("ER  - ") == 2


def test_build_papers_index_includes_papers_without_findings() -> None:
    p_with_finding = _make_paper()
    p_without_finding = _make_paper(
        id="paper.busse-2011",
        citation="Busse L. Visual contrast. Journal of Neuroscience, 2011.",
        authors=["Busse, Laura"],
        year=2011,
        protocol_ids=["protocol.visual-contrast"],
        dataset_ids=[],
        finding_ids=[],
        curation_status="literature-curated",
    )
    finding = _make_finding()

    index = build_papers_index([p_with_finding, p_without_finding], findings=[finding])
    by_id = {paper["id"]: paper for paper in index["papers"]}

    assert set(by_id) == {p_with_finding.id, p_without_finding.id}
    assert by_id[p_with_finding.id]["finding_count"] == 1
    assert by_id[p_with_finding.id]["has_findings"] is True
    assert by_id[p_with_finding.id]["coverage_status"] == "findings"
    assert by_id[p_with_finding.id]["curve_types"] == ["psychometric"]
    assert by_id[p_with_finding.id]["source_data_levels"] == ["processed-trial"]
    assert by_id[p_with_finding.id]["total_n_trials"] == 1200
    assert by_id[p_without_finding.id]["finding_count"] == 0
    assert by_id[p_without_finding.id]["has_findings"] is False
    assert by_id[p_without_finding.id]["coverage_status"] == "protocol-linked"
    assert by_id[p_without_finding.id]["curve_types"] == []
    assert by_id[p_without_finding.id]["source_data_levels"] == []


@pytest.mark.parametrize(
    "paper_id,expected",
    [
        ("paper.roitman-shadlen-2002", "roitman-shadlen-2002"),
        ("plain-id", "plain-id"),
    ],
)
def test_slug_for_paper_id(paper_id: str, expected: str) -> None:
    assert slug_for_paper_id(paper_id) == expected
