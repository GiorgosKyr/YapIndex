# YapIndex

## WSL setup

Use WSL for the GPU environment. Run these commands from PowerShell:

```powershell
wsl
cd "YOUR_PATH/YapIndex"
bash setup_wsl.sh
```

The script creates `.venv`, runs `uv sync`, registers the notebook kernel `YapIndex WSL GPU`, and checks CUDA and FAISS.

## Run the notebook

From WSL:

```bash
code .
```

Open `notebooks/retrieval_eval.ipynb`, select **YapIndex WSL GPU**, and run the cells from top to bottom.

Use `LIMIT = 5` for a quick test. Change it to `None` to evaluate all questions.

## Run the evaluator

```bash
.venv/bin/python retrieval_eval.py
```

The first run downloads the reranker model and may take a few minutes. Later runs use the cached model.
