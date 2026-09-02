#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_root=$(dirname "$script_dir")
runtime_parent="$project_root/apps/desktop/runtime"
runtime_dir="$runtime_parent/python-runtime"
python_version="3.13.5"
python_distribution="cpython-3.13.5-macos-aarch64-none"
python_executable="$runtime_dir/bin/python3.13"
requirements_file="$runtime_parent/runtime-requirements.txt"

if [ -x "$python_executable" ] && PYTHONPATH="$project_root/services/agent/src" \
  "$python_executable" -c "import careerflow_agent, cryptography, docx, fastapi, openai, pypdf, sqlalchemy"; then
  echo "Embedded CareerFlow Python runtime is ready."
  exit 0
fi

if [ -e "$runtime_dir" ] && [ ! -x "$python_executable" ]; then
  echo "Incomplete runtime exists at $runtime_dir; move it aside and run this command again." >&2
  exit 1
fi

mkdir -p "$runtime_parent"
if [ ! -x "$python_executable" ]; then
  uv python install --install-dir "$runtime_parent" --no-bin "$python_version"
  mv "$runtime_parent/$python_distribution" "$runtime_dir"
fi
uv export \
  --quiet \
  --project "$project_root/services/agent" \
  --frozen \
  --no-dev \
  --no-emit-project \
  --format requirements.txt \
  --output-file "$requirements_file"
uv pip sync \
  --quiet \
  --break-system-packages \
  --python "$python_executable" \
  "$requirements_file"
PYTHONPATH="$project_root/services/agent/src" \
  "$python_executable" -c "import careerflow_agent, cryptography, docx, fastapi, openai, pypdf, sqlalchemy"
echo "Embedded CareerFlow Python runtime is ready."
