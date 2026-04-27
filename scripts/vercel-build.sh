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

echo "▶ Building Astro app"
cd web
bun install --frozen-lockfile
bun run build

echo "✓ Vercel build complete; output in web/dist"
