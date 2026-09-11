RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


def load_reranker(
	model_name: str = RERANKER_MODEL,
	device: str = "cuda",
):
	from sentence_transformers import CrossEncoder

	print(f"Loading reranker model '{model_name}' on device '{device}'...")
	return CrossEncoder(model_name, device=device)


def rerank_results(reranker, query: str, documents):
	print(f"Reranking {len(documents)} documents...")
	pairs = [(query, document.page_content) for document in documents]
	scores = reranker.predict(
		pairs,
		batch_size=16,
		show_progress_bar=False,
	)

	ranked = sorted(
		zip(scores, documents),
		key=lambda item: item[0],
		reverse=True,
	)

	return [document for _, document in ranked]
