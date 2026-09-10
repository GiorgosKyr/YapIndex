import faiss
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS


EMBEDDING_MODEL = "nomic-embed-text"


def load_embeddings(model_name: str = EMBEDDING_MODEL):
    return OllamaEmbeddings(model=model_name)


def load_vectorstore(
    index_path: str = "faiss_index",
    model_name: str = EMBEDDING_MODEL,
    use_gpu: bool = True,
    gpu_id: int = 0,
):
    embeddings = load_embeddings(model_name)
    vectorstore = FAISS.load_local(
        index_path,
        embeddings,
        allow_dangerous_deserialization=True,
    )

    if not use_gpu:
        return vectorstore

    if faiss.get_num_gpus() < 1:
        raise RuntimeError("FAISS GPU support is unavailable.")

    resources = faiss.StandardGpuResources()
    vectorstore.index = faiss.index_cpu_to_gpu(
        resources,
        gpu_id,
        vectorstore.index,
    )
    vectorstore._faiss_gpu_resources = resources
    return vectorstore
