import os
import tempfile
import uuid
from typing import Dict, Any, Optional

from langchain.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMBEDDINGS = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

DOCUMENT_STORE_PATH = os.environ.get("DOCUMENT_STORE_PATH", "document_store")
CHROMA_PERSIST_DIRECTORY = os.path.join(DOCUMENT_STORE_PATH, "chroma_db")

os.makedirs(DOCUMENT_STORE_PATH, exist_ok=True)
os.makedirs(CHROMA_PERSIST_DIRECTORY, exist_ok=True)

vector_store = Chroma(
    persist_directory=CHROMA_PERSIST_DIRECTORY,
    embedding_function=EMBEDDINGS
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

groq_api_key = os.getenv("GROQ_API_KEY")
if groq_api_key:
    try:
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192", 
            temperature=0.1,
            max_tokens=1024
        )
        logger.info("Groq API initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Groq API: {e}")
        llm = None
else:
    logger.warning("GROQ_API_KEY not found in environment variables. Answer generation will be limited.")
    llm = None

# simple prompt template for the RAG
qa_template = """
You are a helpful AI assistant that answers questions based on the provided context.
If you don't know the answer based on the context, just say that you don't know.
Don't try to make up an answer.

Context:
{context}

Question: {question}

Answer:
"""

QA_PROMPT = PromptTemplate(
    template=qa_template,
    input_variables=["context", "question"]
)

def get_document_loader(file_path: str, file_type: str):
    """
    This function gets the appropriate document loader based on file type.
    """
    if file_type.lower() == 'pdf':
        return PyPDFLoader(file_path)
    elif file_type.lower() == 'txt':
        return TextLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

async def process_document(
    content: bytes,
    filename: str,
    title: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a document by splitting it into chunks and storing in the vector store.
    """
    file_extension = filename.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # 1. loading the document
        loader = get_document_loader(temp_file_path, file_extension)
        documents = loader.load()

        # 2. splitting the document into chunks
        splits = text_splitter.split_documents(documents)

        # 3. adding the document chunks to the vector store
        collection_name = f"doc_{uuid.uuid4().hex}"
        document_ids = vector_store.add_documents(
            splits,
            collection_name=collection_name
        )
        vector_store.persist()
        document_path = os.path.join(DOCUMENT_STORE_PATH, f"{collection_name}.{file_extension}")
        with open(document_path, 'wb') as f:
            f.write(content)

        return {
            "title": title,
            "description": description,
            "file_path": document_path,
            "file_type": file_extension,
            "collection_name": collection_name,
            "num_chunks": len(splits)
        }
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

async def generate_answer(query: str, retrieved_docs) -> str:
    """
    This function generates an answer to the query based on retrieved documents using Groq API.
    """
    if not retrieved_docs:
        return "No relevant information found to answer your question."
    context = "\n\n".join([doc.page_content for doc in retrieved_docs])
    
    if llm is not None:
        try:
            formatted_prompt = QA_PROMPT.format(context=context, question=query)
            response = llm.invoke(formatted_prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error generating answer with Groq: {e}")
            return f"Based on the retrieved information, here's what I found: {context[:500]}..."
    else:
        return f"Based on the retrieved information, here's what I found: {context[:500]}..."

async def query_documents(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    This function queries the document store with a question and generates an answer.
    """
    retriever = vector_store.as_retriever(
        search_kwargs={"k": top_k}
    )
    docs = retriever.get_relevant_documents(query)
    answer = await generate_answer(query, docs)
    
    results = []
    for doc in docs:
        results.append({
            "content": doc.page_content,
            "metadata": doc.metadata
        })
    
    return {
        "query": query,
        "answer": answer,
        "sources": results,
        "num_results": len(results)
    } 