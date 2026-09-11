import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.faiss_store import load_vectorstore
from utils.generator import load_generator
from utils.rag import answer_question
from utils.reranker import load_reranker

print("Loading FAISS vectorstore...")

vectorstore = load_vectorstore(use_gpu=True)
generator = load_generator()
reranker = load_reranker(device="cuda")

query = "What is the current API v2 EOL date?"

answer, documents = answer_question(
    vectorstore,
    generator,
    query,
    reranker=reranker,
)
print(f"Query: {query}\n")
print("Answer:")

print(answer)

print("\nSources:")
for document in documents:
    print(document.metadata.get("source", "Unknown"))