import json
from pathlib import Path

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from sentence_transformers import CrossEncoder


RETRIEVAL_K = 20
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


def load_vectorstore(index_path: str = "faiss_index"):
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return FAISS.load_local(
        index_path,
        embeddings,
        allow_dangerous_deserialization=True,
    )


def load_questions(
    questions_path: str = "evals/meridian_rag_eval.jsonl",
) -> list[dict]:
    with Path(questions_path).open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def normalize_source(source: str) -> str:
    return source.replace("\\", "/").lstrip("./")


def rerank_results(reranker, query: str, documents):
    pairs = [(query, document.page_content) for document in documents]
    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(scores, documents),
        key=lambda item: item[0],
        reverse=True,
    )

    return [document for _, document in ranked]


def get_sources(documents):
    return [
        normalize_source(document.metadata.get("source", "Unknown"))
        for document in documents
    ]


def score_results(documents, question):
    sources = get_sources(documents)
    gold_sources = {
        normalize_source(source)
        for source in question["gold_sources"]
    }
    distractor_sources = {
        normalize_source(source)
        for source in question.get("distractor_sources", [])
    }

    return {
        "hit_at_3": int(bool(gold_sources & set(sources[:3]))),
        "hit_at_5": int(bool(gold_sources & set(sources[:5]))),
        "hit_at_10": int(bool(gold_sources & set(sources[:10]))),
        "distractor_at_5": int(
            bool(distractor_sources & set(sources[:5]))
        ),
    }


def add_scores(totals, scores):
    for key, value in scores.items():
        totals[key] += value


def print_metrics(label, totals, total_questions):
    print(f"\n{label}")
    print("-" * len(label))
    print(f"Recall@3: {totals['hit_at_3'] / total_questions:.2%}")
    print(f"Recall@5: {totals['hit_at_5'] / total_questions:.2%}")
    print(f"Recall@10: {totals['hit_at_10'] / total_questions:.2%}")
    print(
        "Distractor rate@5: "
        f"{totals['distractor_at_5'] / total_questions:.2%}"
    )


def main():
    print("Loading FAISS vectorstore...")
    vectorstore = load_vectorstore()

    print(f"Loading reranker: {RERANKER_MODEL}")
    reranker = CrossEncoder(
        RERANKER_MODEL,
        device="cuda",
    )

    questions = load_questions()
    print(f"Loaded {len(questions)} questions.")

    before_totals = {
        "hit_at_3": 0,
        "hit_at_5": 0,
        "hit_at_10": 0,
        "distractor_at_5": 0,
    }
    after_totals = before_totals.copy()

    for index, question in enumerate(questions, start=1):
        print(
            f"Evaluating {index}/{len(questions)}...",
            end="\r",
            flush=True,
        )

        before_results = vectorstore.similarity_search(
            question["question"],
            k=RETRIEVAL_K,
        )

        after_results = rerank_results(
            reranker,
            question["question"],
            before_results,
        )

        add_scores(
            before_totals,
            score_results(before_results, question),
        )
        add_scores(
            after_totals,
            score_results(after_results, question),
        )

    total_questions = len(questions)

    print()
    print(f"Total questions evaluated: {total_questions}")
    print_metrics("Before reranking", before_totals, total_questions)
    print_metrics("After reranking", after_totals, total_questions)


if __name__ == "__main__":
    main()