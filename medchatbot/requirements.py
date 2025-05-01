# requirements.py
def install_dependencies():
    import subprocess
    subprocess.run(["pip", "install", "--quiet", 
        "langchain", "langchain-community", "langchain_groq", "sentence-transformers",
        "unstructured", "pandas", "qdrant_client", "langchain_huggingface", 
        "langchain_qdrant", "pypdf", "jq"
    ])
