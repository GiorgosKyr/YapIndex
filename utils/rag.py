from langchain_core.documents import Document

from utils.generator import generate_answer
from utils.reranker import rerank_results

def retrieve_documents(vector_store, query: str, retrieval_k: int =  20, final_k: int = 5, reranker=None) -> list[Document]:

    documents = vector_store.similarity_search(query, k=retrieval_k)

    if reranker is not None:
        documents = rerank_results(reranker, query, documents)

    return documents[:final_k]

def answer_question(
    vector_store,
    generator,
    question: str,
    retrieval_k: int = 20,
    final_k: int = 5,
    reranker=None,
) -> tuple[str, list[Document]]:
    documents = retrieve_documents(vector_store, question, retrieval_k, final_k, reranker)
    answer = generate_answer(generator, question, documents)
    return answer, documents