# data_loader.py
# from langchain.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import CSVLoader

def load_and_split_docs(csv_path):
    loader = CSVLoader(file_path=csv_path, encoding='utf-8') 
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_docs = splitter.split_documents(documents)
    return documents, split_docs, splitter
