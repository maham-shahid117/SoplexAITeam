# from requirements import install_dependencies
# install_dependencies()
# main.py
from SoplexAITeam.medchatbot.requirements import install_dependencies
from SoplexAITeam.medchatbot.data_loader import load_and_split_docs
from SoplexAITeam.medchatbot.embedder import get_embeddings
from SoplexAITeam.medchatbot.retriever import prepare_documents, create_qdrant_store
from SoplexAITeam.medchatbot.qa_chain import create_qa_chain

def main():
    install_dependencies()

    csv_path = "medquad.csv"
    documents, split_docs, splitter = load_and_split_docs(csv_path)
    
    embeddings = get_embeddings()
    doc_list = prepare_documents(documents, splitter)
    
    qdrant_store = create_qdrant_store(doc_list, embeddings)

    query = "What causes Glaucoma?"
    results = qdrant_store.similarity_search(query, k=5)
    
    chain = create_qa_chain(results)
    response = chain.invoke("What is Human Phenotype Ontology?")
    print(response)

if __name__ == "__main__":
    main()
