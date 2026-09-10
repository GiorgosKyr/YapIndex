#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

export UV_LINK_MODE=copy

echo "Creating WSL virtual environment in $PROJECT_ROOT/.venv"
uv venv --python 3.11

echo "Installing project dependencies"
uv sync

echo "Registering the Jupyter kernel"
.venv/bin/python -m ipykernel install --user \
    --name yapindex-wsl-gpu \
    --display-name "YapIndex WSL GPU"

echo "Checking CUDA and FAISS"
.venv/bin/python -c '
import sys
import torch
import faiss

if not torch.cuda.is_available():
    raise SystemExit("CUDA is unavailable in this WSL environment.")

print(f"Python: {sys.executable}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"FAISS GPUs: {faiss.get_num_gpus()}")
'

echo
echo "Setup complete. Open the notebook and select: YapIndex WSL GPU"
