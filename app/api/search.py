from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Category
from app.schemas import (
    SearchRequest, SearchResponse, SearchResult,
    SummarizeRequest, SummarizeResponse,
    QARequest, QAResponse,
    FindPassagesRequest, FindPassagesResponse
)
from app.services.embeddings import embeddings_service
from app.services.vector_store import vector_store_service
from app.services.gemini_service import gemini_service
from loguru import logger

router = APIRouter(prefix="/api/search", tags=["Search"])

def distance_to_confidence(distance: float) -> float:
    """Convert cosine distance to confidence score"""
    # Cosine distance is 0-2, convert to confidence 0-1
    # Lower distance = higher confidence
    confidence = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
    return round(confidence, 2)

@router.post("/query", response_model=SearchResponse)
def search_query(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Semantic search across documents in a category
    """
    
    # Validate category exists
    category = db.query(Category).filter(Category.id == request.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Generate query embedding
        query_embedding = embeddings_service.generate_embedding(request.query)
        
        # Search vector store
        search_results = vector_store_service.search(
            query_embedding=query_embedding,
            category_id=request.category_id,
            top_k=request.top_k
        )
        
        if not search_results:
            return SearchResponse(
                answer="No relevant documents found for your query.",
                confidence_score=0.0,
                results=[]
            )
        
        # Extract context chunks
        context_chunks = [result["text"] for result in search_results]
        
        # Generate answer using Gemini
        answer, confidence = gemini_service.generate_answer(request.query, context_chunks)
        
        # Format results
        formatted_results = []
        for result in search_results:
            formatted_results.append(SearchResult(
                chunk_id=result["chunk_id"],
                text=result["text"],
                confidence_score=distance_to_confidence(result.get("distance", 1.0))
            ))
        
        return SearchResponse(
            answer=answer,
            confidence_score=confidence,
            results=formatted_results
        )
    
    except Exception as e:
        logger.error(f"Error in search query: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.post("/summarize", response_model=SummarizeResponse)
def summarize_category(request: SummarizeRequest, db: Session = Depends(get_db)):
    """
    Summarize all documents in a category
    """
    
    # Validate category exists
    category = db.query(Category).filter(Category.id == request.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Get all chunks from category
        all_chunks = vector_store_service.get_all_chunks_by_category(request.category_id)
        
        if not all_chunks:
            return SummarizeResponse(
                summary="No documents found in this category.",
                confidence_score=0.0
            )
        
        # Extract texts (limit to prevent token overflow)
        texts = [chunk["text"] for chunk in all_chunks[:50]]
        
        # Generate summary
        summary, confidence = gemini_service.summarize_documents(texts, request.max_length)
        
        return SummarizeResponse(
            summary=summary,
            confidence_score=confidence
        )
    
    except Exception as e:
        logger.error(f"Error in summarize: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization error: {str(e)}")

@router.post("/qa", response_model=QAResponse)
def question_answer(request: QARequest, db: Session = Depends(get_db)):
    """
    Answer a specific question based on documents in a category
    """
    
    # Validate category exists
    category = db.query(Category).filter(Category.id == request.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Generate query embedding
        query_embedding = embeddings_service.generate_embedding(request.question)
        
        # Search vector store
        search_results = vector_store_service.search(
            query_embedding=query_embedding,
            category_id=request.category_id,
            top_k=request.top_k
        )
        
        if not search_results:
            return QAResponse(
                answer="I couldn't find relevant information to answer your question.",
                confidence_score=0.0,
                relevant_chunks=[]
            )
        
        # Extract context chunks
        context_chunks = [result["text"] for result in search_results]
        
        # Answer question using Gemini
        answer, confidence = gemini_service.answer_question(request.question, context_chunks)
        
        # Format relevant chunks
        relevant_chunks = []
        for result in search_results:
            relevant_chunks.append(SearchResult(
                chunk_id=result["chunk_id"],
                text=result["text"],
                confidence_score=distance_to_confidence(result.get("distance", 1.0))
            ))
        
        return QAResponse(
            answer=answer,
            confidence_score=confidence,
            relevant_chunks=relevant_chunks
        )
    
    except Exception as e:
        logger.error(f"Error in Q&A: {e}")
        raise HTTPException(status_code=500, detail=f"Q&A error: {str(e)}")

@router.post("/find-passages", response_model=FindPassagesResponse)
def find_passages(request: FindPassagesRequest, db: Session = Depends(get_db)):
    """
    Find relevant passages based on a query
    """
    
    # Validate category exists
    category = db.query(Category).filter(Category.id == request.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Generate query embedding
        query_embedding = embeddings_service.generate_embedding(request.query)
        
        # Search vector store
        search_results = vector_store_service.search(
            query_embedding=query_embedding,
            category_id=request.category_id,
            top_k=request.top_k
        )
        
        # Format passages
        passages = []
        for result in search_results:
            passages.append(SearchResult(
                chunk_id=result["chunk_id"],
                text=result["text"],
                confidence_score=distance_to_confidence(result.get("distance", 1.0))
            ))
        
        return FindPassagesResponse(
            passages=passages,
            total_found=len(passages)
        )
    
    except Exception as e:
        logger.error(f"Error finding passages: {e}")
        raise HTTPException(status_code=500, detail=f"Find passages error: {str(e)}")
