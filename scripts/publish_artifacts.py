"""Bundle the slice-report artifacts referenced by each vertical slice and
publish them as a GitHub Release asset.

Usage:
    uv run python scripts/publish_artifacts.py [--dry-run]

Requires: gh CLI authenticated; run from the repo root.

Selects only the files referenced by slice.yaml `artifact_links` of type
"derived", plus each slice's report_path / analysis_result_path /
primary_artifact_path. Raw trial CSVs and other large local-only files are
excluded by construction because slice manifests do not link to them.

The Vercel build downloads the latest release tarball and extracts it into
web/public/, so the asset path layout matches the URLs that slice reports
expect (e.g. auditory_clicks/report.html → /auditory_clicks/report.html).
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "derived"

# Make sure the package is importable when running via `python scripts/...`
# rather than `uv run`.
sys.path.insert(0, str(ROOT / "src"))

from behavtaskatlas.static_site import load_vertical_slice_records  # noqa: E402


def collect_paths() -> list[Path]:
    """Return the set of derived-relative paths to include in the bundle."""
    seen: set[Path] = set()
    missing: list[str] = []

    def add(path_str: str | None) -> None:
        if not path_str:
            return
        relative = Path(path_str)
        absolute = DERIVED / relative
        if absolute.exists():
            seen.add(relative)
        else:
            missing.append(str(relative))

    for record in load_vertical_slice_records(ROOT):
        add(record.report_path)
        add(record.analysis_result_path)
        add(record.primary_artifact_path)
        for link in record.artifact_links:
            if link.path_type == "derived":
                add(link.path)

    if missing:
        print(
            "warning: the following manifest paths are not present locally and "
            "will not be bundled:",
            file=sys.stderr,
        )
        for path in sorted(set(missing)):
            print(f"  - {path}", file=sys.stderr)

    return sorted(seen)


def git_short_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], text=True
    ).strip()


def git_dirty() -> bool:
    output = subprocess.check_output(
        ["git", "status", "--porcelain"], text=True
    ).strip()
    return bool(output)


def build_tarball(paths: list[Path], destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as tar:
        for relative in paths:
            tar.add(DERIVED / relative, arcname=str(relative))
    return destination.stat().st_size


def release_notes(paths: list[Path], commit: str, dirty: bool) -> str:
    slice_dirs = sorted({path.parts[0] for path in paths if path.parts})
    lines = [
        "Bundled slice-report artifacts for the public deploy.",
        "",
        f"- Source commit: `{commit}`{' (dirty working tree)' if dirty else ''}",
        f"- Files: {len(paths)}",
        "- Slice directories:",
    ]
    for slice_dir in slice_dirs:
        lines.append(f"  - `{slice_dir}/`")
    lines.append("")
    lines.append(
        "Vercel pulls the latest release of this kind during build and extracts "
        "it into `web/public/`."
    )
    return "\n".join(lines)


def gh_release_create(
    *,
    tag: str,
    title: str,
    notes: str,
    asset: Path,
    dry_run: bool,
) -> None:
    cmd = [
        "gh",
        "release",
        "create",
        tag,
        str(asset),
        "--title",
        title,
        "--notes",
        notes,
        "--latest",
    ]
    if dry_run:
        print("dry-run: would invoke", " ".join(json.dumps(arg) for arg in cmd))
        return
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the tarball and print the gh command, but do not publish.",
    )
    parser.add_argument(
        "--keep-tarball",
        action="store_true",
        help="Keep the temporary tarball after publishing.",
    )
    args = parser.parse_args()

    paths = collect_paths()
    if not paths:
        print("error: no artifact paths found; nothing to publish", file=sys.stderr)
        return 2

    commit = git_short_sha()
    dirty = git_dirty()
    today = datetime.date.today().isoformat()
    tag = f"slice-artifacts-{today}-{commit}"
    title = f"Slice artifacts {today}"
    notes = release_notes(paths, commit, dirty)

    with tempfile.TemporaryDirectory(prefix="behavtaskatlas-artifacts-") as tmpdir:
        tarball = Path(tmpdir) / "slice-artifacts.tar.gz"
        size_bytes = build_tarball(paths, tarball)
        size_mb = size_bytes / (1024 * 1024)
        print(
            f"Built {tarball.name} ({size_mb:.2f} MB) covering {len(paths)} files."
        )
        if args.keep_tarball:
            keep_path = ROOT / "slice-artifacts.tar.gz"
            keep_path.write_bytes(tarball.read_bytes())
            print(f"Kept tarball at {keep_path}")
        gh_release_create(
            tag=tag,
            title=title,
            notes=notes,
            asset=tarball,
            dry_run=args.dry_run,
        )
    print(f"Published release {tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
