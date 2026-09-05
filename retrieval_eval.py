import json
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings

def load_vectorstore(index_path: str = "faiss_index"):
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return FAISS.load_local(
        index_path,
        embeddings,
        allow_dangerous_deserialization=True,
    )

def load_questions(questions_path: str = "questions.json") -> list[dict]:
    with Path(questions_path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def main():

    print("Loading FAISS vectorstore from 'faiss_index' folder...")
    vectorstore = load_vectorstore("faiss_index")

    print("Loading questions from 'evals/meridian_rag_eval.jsonl'...")
    questions = load_questions("evals/meridian_rag_eval.jsonl")

    print(f"Loaded {len(questions)} questions for evaluation.\n")

    hits_at_3 = 0
    hits_at_5 = 0
    hits_at_10 = 0
    distractor_hits = 0

    misses = []
    distractor_cases = []

    for i, question in enumerate(questions, start=1):

        print(f"Evaluating {i}/{len(questions)}...", end="\r")

        results = vectorstore.similarity_search(question["question"], k=10)
        sources = [result.metadata.get("source", "Unknown") for result in results]

        gold_sources = set(question["gold_sources"])
        distractor_sources = set(question.get("distractor_sources", []))

        hits_at_3 += int(any(source in gold_sources for source in sources[:3]))
        hits_at_5 += int(any(source in gold_sources for source in sources[:5]))
        hits_at_10 += int(any(source in gold_sources for source in sources[:10]))
        distractor_hits += int(
            any(source in distractor_sources for source in sources[:5])
        )

        retrieved_at_10 = set(sources[:10])
        retrieved_at_5 = set(sources[:5])


        if not gold_sources.intersection(retrieved_at_10):
            misses.append(
                {
                    "question": question["question"],
                    "gold_sources": list(gold_sources),
                    "retrieved_sources": list(retrieved_at_10),
                }
            )

        if distractor_sources.intersection(retrieved_at_5):
            distractor_cases.append(
                {
                    "question": question["question"],
                    "distractor_sources": list(distractor_sources),
                    "retrieved_sources": list(retrieved_at_5),
                }
            )
    total_questions = len(questions)

    print(f"Total questions evaluated: {total_questions}")
    print(f"Hits at 3: {hits_at_3} ({(hits_at_3 / total_questions) * 100:.2f}%)")
    print(f"Hits at 5: {hits_at_5} ({(hits_at_5 / total_questions) * 100:.2f}%)")
    print(f"Hits at 10: {hits_at_10} ({(hits_at_10 / total_questions) * 100:.2f}%)")
    print(f"Distractor hits: {distractor_hits} ({(distractor_hits / total_questions) * 100:.2f}%)")


    print("\nMisses:")
    for miss in misses:
        print(f"Question: {miss['question']}")
        print(f"Gold sources: {miss['gold_sources']}")
        print(f"Retrieved sources: {miss['retrieved_sources']}\n")
        print("-" * 80)

    print("\nDistractor cases:")
    for distractor_case in distractor_cases:
        print(f"Question: {distractor_case['question']}")
        print(f"Distractor sources: {distractor_case['distractor_sources']}")
        print(f"Retrieved sources: {distractor_case['retrieved_sources']}\n")
        print("-" * 80)

        
if __name__ == "__main__":
    main()