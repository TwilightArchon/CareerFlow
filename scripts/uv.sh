#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
UV_CACHE_DIR=${UV_CACHE_DIR:-"$project_root/.tools/uv-cache"}
export UV_CACHE_DIR

if command -v uv >/dev/null 2>&1; then
  exec uv "$@"
fi

local_uv="$project_root/.tools/uv/bin/uv"

if [ ! -x "$local_uv" ]; then
  echo "uv is not installed. Run: python3 -m venv .tools/uv && .tools/uv/bin/pip install uv" >&2
  exit 127
fi

exec "$local_uv" "$@"
