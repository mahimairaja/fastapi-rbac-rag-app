from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.auth.jwt import get_current_active_user
from app.auth.authorization import authorize, require_permission
from app.services.rag_service import process_document, query_documents
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])

class DocumentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    file_type: str
    uploader_id: int
    
    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SourceResponse(BaseModel):
    content: str
    metadata: Dict[str, Any]

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceResponse]
    num_results: int


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    To upload and process a document for RAG.
    """
    if not authorize(current_user, "upload", "document"):
        logger.error(f"User {current_user.username} not authorized to upload documents")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload documents"
        )
    
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ["pdf", "txt"]:
        logger.error(f"Unsupported file type: {file_extension}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF and TXT files are supported."
        )
    
    content = await file.read()
    
    try:
        doc_metadata = await process_document(
            content=content,
            filename=file.filename,
            title=title,
            description=description
        )
        db_document = Document(
            title=title,
            description=description,
            file_path=doc_metadata["file_path"],
            file_type=doc_metadata["file_type"],
            uploader_id=current_user.id
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        logger.info(f"Document {db_document.title} uploaded successfully by user {current_user.username}")
        
        return db_document
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    To list all accessible documents.
    """
    if not authorize(current_user, "read", "document"):
        logger.error(f"User {current_user.username} not authorized to access documents")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access documents"
        )
    
    if current_user.role in ["admin", "moderator"]:
        documents = db.query(Document).offset(skip).limit(limit).all()
    else:
        documents = db.query(Document).filter(Document.uploader_id == current_user.id).offset(skip).limit(limit).all()
    
    logger.info(f"Listed {len(documents)} documents for user {current_user.username}")
    return documents


@router.post("/query", response_model=QueryResponse)
async def query_rag(
    query_request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    To query documents using RAG.
    """
    if not authorize(current_user, "use", "rag"):
        logger.error(f"User {current_user.username} not authorized to use RAG")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to use RAG"
        )
    try:
        results = await query_documents(
            query=query_request.query,
            top_k=query_request.top_k
        )
        logger.info(f"Query {query_request.query} executed successfully by user {current_user.username}")
        return results
    
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying documents: {str(e)}"
        ) 