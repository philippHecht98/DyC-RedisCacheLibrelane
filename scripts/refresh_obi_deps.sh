#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBI_DIR="$REPO_ROOT/obi"
COMMON_CELLS_LINK="$OBI_DIR/common_cells"
LEGACY_COMMON_CELLS_LINK="$REPO_ROOT/third_party/common_cells"

if ! command -v bender >/dev/null 2>&1; then
  echo "Error: bender is not installed or not on PATH." >&2
  exit 1
fi

if [[ ! -d "$OBI_DIR" ]]; then
  echo "Error: expected OBI repository at $OBI_DIR" >&2
  exit 1
fi

pushd "$OBI_DIR" >/dev/null
bender update

cf_math_pkg_path="$(find .bender -type f -path "*/common_cells-*/src/cf_math_pkg.sv" | head -n 1 || true)"
if [[ -z "$cf_math_pkg_path" ]]; then
  echo "Error: could not locate cf_math_pkg.sv after 'bender update'." >&2
  exit 1
fi

common_cells_root="$(dirname "$(dirname "$cf_math_pkg_path")")"
popd >/dev/null

ln -sfn "$OBI_DIR/$common_cells_root" "$COMMON_CELLS_LINK"

if [[ -L "$LEGACY_COMMON_CELLS_LINK" ]]; then
  rm -f "$LEGACY_COMMON_CELLS_LINK"
fi

echo "Refreshed OBI dependencies."
echo "common_cells -> $COMMON_CELLS_LINK"
echo "cf_math_pkg -> $COMMON_CELLS_LINK/src/cf_math_pkg.sv"
