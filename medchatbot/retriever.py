# retriever.py
from langchain.docstore.document import Document
from langchain_qdrant import QdrantVectorStore
from SoplexAITeam.medchatbot.config import QDRANT_URL, QDRANT_KEY, COLLECTION_NAME

def prepare_documents(documents, splitter):
    doc_list = []
    for page in documents:
        splits = splitter.split_text(page.page_content)
        for pg in splits:
            page_no = page.metadata.get("page", "Unknown")
            metadata = {"source": "Practice Session", "page_no": page_no}
            doc = Document(page_content=pg, metadata=metadata)
            doc_list.append(doc)
    return doc_list

def create_qdrant_store(doc_list, embeddings):
    return QdrantVectorStore.from_documents(
        doc_list,
        embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_KEY,
        collection_name=COLLECTION_NAME
    )
