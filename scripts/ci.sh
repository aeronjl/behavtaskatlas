#!/usr/bin/env bash
# CI script: the same checks run locally and in GitHub Actions.
# The GitHub workflow is intentionally a thin wrapper around this file
# so that any contributor can reproduce the gate without leaving their
# machine.
#
# Usage:
#   bash scripts/ci.sh
#
# Requires uv and bun on PATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

step() { printf '\n▶ %s\n' "$1"; }

step "Checking required tooling"
command -v uv >/dev/null 2>&1 || {
  echo "missing 'uv' on PATH (https://docs.astral.sh/uv/)" >&2
  exit 1
}
command -v bun >/dev/null 2>&1 || {
  echo "missing 'bun' on PATH (https://bun.sh/)" >&2
  exit 1
}

step "Installing Python deps (base + dev)"
uv sync --group dev

step "Linting Python (ruff check src tests)"
uv run ruff check src tests

step "Validating YAML records (behavtaskatlas validate)"
uv run behavtaskatlas validate

step "Running Python tests (pytest)"
uv run pytest

step "Auditing findings (pooled vs by-subject reconciliation)"
uv run behavtaskatlas audit-findings

step "Auditing model fits (forward-eval drift detection)"
uv run behavtaskatlas audit-models

step "Exporting static JSON (behavtaskatlas site-index)"
uv run behavtaskatlas site-index

step "Installing JS deps (bun install --frozen-lockfile)"
( cd web && bun install --frozen-lockfile )

step "Type-checking Astro (bun run check)"
( cd web && bun run check )

step "Building Astro (bun run build)"
( cd web && bun run build )

printf '\n✓ CI complete\n'
