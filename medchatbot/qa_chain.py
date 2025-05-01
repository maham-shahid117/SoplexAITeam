# qa_chain.py
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnableLambda
from langchain_groq import ChatGroq

from SoplexAITeam.medchatbot.config import GROQ_API_KEY

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def create_qa_chain(retrieved_docs):
    template = """
Answer the question based only on the following context:
{context}

Question: {question}
"""
    prompt = PromptTemplate.from_template(template)
    llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile")
    
    chain = (
        RunnableLambda(lambda x: {"context": format_docs(retrieved_docs), "question": x})
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain
