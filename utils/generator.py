from langchain_ollama import ChatOllama
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

GENERATOR_MODEL = "qwen2.5:7b"

def load_generator():
    return ChatOllama(model=GENERATOR_MODEL, temperature=0)

def build_prompt(question: str, documents: list[Document]) -> str:

    context = "\n\n".join(
        f"Source: {doc.metadata.get('source', 'Unknown')}\n"
        f"{doc.page_content}"
        for doc in documents
    )

    return f"""
        Answer the question using only the context below.

        If the context does not contain enough information, say:
        "The knowledge base does not contain enough information."

        Do not guess. Cite sources using their paths.

        Question:
        {question}

        Context:
        {context}
    """

def generate_answer(generator, question: str, documents: list[Document]) -> str:

    if not documents:
        return "The knowledge base does not contain enough information."

    response = generator.invoke([HumanMessage(content=build_prompt(question, documents))])

    return response.content