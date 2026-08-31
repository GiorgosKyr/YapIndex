from pathlib import Path

from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS


def load_docs():
    docs_path = Path("company")
    documents = []

    for file_path in docs_path.rglob("*.md"):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        documents.append(
            Document(page_content=text, metadata={"source": str(file_path)})
        )

    print(f"Loaded {len(documents)} documents from {docs_path}")
    return documents


def split_docs(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    split_documents = text_splitter.split_documents(documents)
    print(f"Split into {len(split_documents)} chunks")
    return split_documents


def embed_and_store_documents(split_documents):

    embedder_model = "nomic-embed-text"

    embedder = OllamaEmbeddings(model=embedder_model)
    print(f"Using Ollama embeddings model: {embedder_model}")

    print("Embedding chunks...")
    for i, chunk in enumerate(split_documents, start=1):
        print(f"  [{i}/{len(split_documents)}] embedding chunk", end="\r")
        _ = embedder.embed_query(chunk.page_content)

    print("\nBuilding FAISS vectorstore...")
    vectorstore = FAISS.from_documents(split_documents, embedder)
    print(f"FAISS vectorstore built with {len(split_documents)} vectors")

    vectorstore.save_local("faiss_index")
    print("Saved FAISS vectorstore to 'faiss_index' folder")

    return vectorstore

def main():

    documents = load_docs()
    split_documents = split_docs(documents)
    print(f"Embedding and storing {len(split_documents)} split documents...")
    embed_and_store_documents(split_documents)


if __name__ == "__main__":
    main()