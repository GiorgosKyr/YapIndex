# YapIndex

## Environment

YapIndex must run in a Linux environment because the project uses Linux FAISS GPU
packages. Supported environments are:

- Native Linux with an NVIDIA GPU and working CUDA drivers.
- Windows 10/11 with WSL2, an NVIDIA GPU, and the WSL CUDA driver support.

Running the project directly with Windows Python is not supported.

## Native Linux setup

From a Linux terminal in the project directory:

```bash
chmod +x setup_wsl.sh
./setup_wsl.sh
```

The script name is historical; it also works in a native Linux environment. It
creates `.venv`, runs `uv sync`, registers the notebook kernel, and checks CUDA
and FAISS.

## Windows setup with WSL2

Install WSL2 and an Ubuntu distribution first. In PowerShell, start WSL and
open the project directory:

```powershell
wsl
cd "/mnt/c/.../YapIndex"
./setup_wsl.sh
```

If the project is stored elsewhere on the Windows drive, replace the path with
its WSL-mounted equivalent, such as `/mnt/c/...`.

## Open in VS Code with WSL

From the WSL terminal, while inside the project directory:

```bash
code .
```

In VS Code:

1. Confirm the bottom-left indicator says **WSL**. If it does not, install the
	**WSL** extension and choose **WSL: Reopen Folder in WSL** from the Command
	Palette.
2. Open `notebooks/retrieval_eval.ipynb`.
3. Use the kernel picker in the notebook toolbar and select **YapIndex WSL GPU**.
4. Run the cells from top to bottom.

Do not select a Windows Python or Conda kernel. The notebook should report the
NVIDIA GPU, `FAISS GPUs: 1`, `FAISS index: GpuIndexFlat`, and `Device: cuda:0`.

Use `LIMIT = 5` for a quick test. Change it to `None` to evaluate all questions.

## Run the evaluator

From the Linux or WSL terminal:

```bash
.venv/bin/python retrieval_eval.py
```

The first run downloads the reranker model and may take a few minutes. Later runs use the cached model.
