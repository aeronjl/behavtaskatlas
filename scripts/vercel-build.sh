#!/usr/bin/env bash
set -euo pipefail

# Vercel build entry point.
# Runs the Python static-site exporter (which produces derived/*.json from
# the YAML records) and then the Astro build, which inlines those JSONs.
#
# Slice report HTML/SVG artifacts are NOT regenerated here — those require
# downloading raw NWB/MAT files and minutes-to-hours of compute, which
# belongs in CI (Phase 4), not in a Vercel build. The Astro app currently
# links to slice reports by relative path; until Phase 4 ships, those links
# 404 in production, while catalog/protocols/datasets pages work normally.

echo "▶ Installing uv"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "▶ Installing bun"
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"

echo "▶ Validating records and exporting static JSON"
uv sync
uv run behavtaskatlas validate
uv run behavtaskatlas site-index

echo "▶ Fetching latest slice-artifacts release into web/public/"
PUBLIC_DIR="web/public"
mkdir -p "$PUBLIC_DIR"
RELEASES_URL="https://api.github.com/repos/aeronjl/behavtaskatlas/releases?per_page=20"
ASSET_URL="$(
  curl -sSL -H "Accept: application/vnd.github+json" "$RELEASES_URL" \
    | python3 -c '
import json, sys
data = json.load(sys.stdin)
candidate = next(
    (
        rel for rel in data
        if rel.get("tag_name", "").startswith("slice-artifacts-")
        and not rel.get("draft")
        and not rel.get("prerelease")
    ),
    None,
)
if candidate is None:
    sys.exit(0)
for asset in candidate.get("assets", []):
    if asset.get("name", "").endswith(".tar.gz"):
        print(asset["browser_download_url"])
        break
'
)"
if [ -n "${ASSET_URL:-}" ]; then
  echo "Downloading $ASSET_URL"
  curl -sSL -o /tmp/slice-artifacts.tar.gz "$ASSET_URL"
  tar -xzf /tmp/slice-artifacts.tar.gz -C "$PUBLIC_DIR"
  echo "Extracted slice artifacts into $PUBLIC_DIR"
else
  echo "No slice-artifacts release found; slice report URLs will 404 in this deploy."
fi

echo "▶ Building Astro app"
cd web
bun install --frozen-lockfile
bun run build

echo "✓ Vercel build complete; output in web/dist"
