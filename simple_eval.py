from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings

def load_faiss_index(index_path: str = "faiss_index"):

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return FAISS.load_local(
        index_path,
        embeddings,
        allow_dangerous_deserialization=True,
    )
    

def main():
    
    query = "What is the current API v2 EOL date?"

    print("Loading FAISS vectorstore from 'faiss_index' folder...")
    vectorstore = load_faiss_index("faiss_index")

    results = vectorstore.similarity_search(query, k=3)

    print(f"Query: {query}\n")
    for i, result in enumerate(results, start=1):
        print(f"Result {i}:")
        print(f"Source: {result.metadata.get('source', 'Unknown')}")
        print(f"Content: {result.page_content}\n")
        print("-" * 80)



if __name__ == "__main__":
    main()