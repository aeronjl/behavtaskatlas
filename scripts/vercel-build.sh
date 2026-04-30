#!/usr/bin/env bash
set -euo pipefail

# Vercel build entry point.
#
# Order of operations:
#   1. Install uv + bun.
#   2. Sync the Python project + uv run validate.
#   3. Fetch the latest slice-artifacts release tarball and extract it into
#      both derived/ (so behavtaskatlas site-index can see the slice reports
#      and stamp them "Report available" in manifest.json) and web/public/
#      (so Astro's static pipeline bundles them at the URL paths that slice
#      manifests reference).
#   4. uv run site-index against the populated derived/.
#   5. bun install + bun run build.
#
# Heavy slice analyses are not regenerated in the Vercel build; they live in
# the release tarball, produced locally or by the manual slice-artifacts
# workflow. The build is fast (sub-2-min) because it only stitches existing
# artifacts together with freshly-validated YAML.

echo "▶ Installing uv"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "▶ Installing bun"
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"

echo "▶ Syncing Python project"
uv sync

echo "▶ Validating records"
uv run behavtaskatlas validate
export BEHAVTASKATLAS_ASSUME_CLEAN=1

echo "▶ Fetching latest slice-artifacts release"
PUBLIC_DIR="web/public"
mkdir -p "$PUBLIC_DIR" derived
# Pull the list and sort by published_at descending; pick the newest non-draft
# non-prerelease tag prefixed slice-artifacts-. /releases ordering is not
# documented as deterministic for this repo (we have observed oldest-first
# results), so sort explicitly rather than trusting input order.
RELEASES_URL="https://api.github.com/repos/aeronjl/behavtaskatlas/releases?per_page=20"
ASSET_URL="$(
  curl -sSL -H "Accept: application/vnd.github+json" "$RELEASES_URL" \
    | python3 -c '
import json, sys
data = json.load(sys.stdin)
candidates = [
    rel for rel in data
    if rel.get("tag_name", "").startswith("slice-artifacts-")
    and not rel.get("draft")
    and not rel.get("prerelease")
]
candidates.sort(key=lambda rel: rel.get("published_at") or "", reverse=True)
if not candidates:
    sys.exit(0)
for asset in candidates[0].get("assets", []):
    if asset.get("name", "").endswith(".tar.gz"):
        print(asset["browser_download_url"])
        break
'
)"
if [ -n "${ASSET_URL:-}" ]; then
  echo "Downloading $ASSET_URL"
  curl -sSL -o /tmp/slice-artifacts.tar.gz "$ASSET_URL"
  tar -xzf /tmp/slice-artifacts.tar.gz -C derived
  tar -xzf /tmp/slice-artifacts.tar.gz -C "$PUBLIC_DIR"
  echo "Extracted slice artifacts into derived/ and $PUBLIC_DIR"
else
  echo "No slice-artifacts release found; slice report URLs will 404 in this deploy."
fi

echo "▶ Exporting static JSON (now sees extracted slice artifacts)"
uv run behavtaskatlas site-index

echo "▶ Building Astro app"
cd web
bun install --frozen-lockfile
bun run build

echo "✓ Vercel build complete; output in web/dist"
