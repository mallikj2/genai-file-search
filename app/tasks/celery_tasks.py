from celery import Celery
from app.config import settings
from app.database import SessionLocal
from app.models import File, Chunk
from app.services.file_processor import file_processor
from app.services.chunking import chunking_service
from app.services.embeddings import embeddings_service
from app.services.vector_store import vector_store_service
from loguru import logger
from datetime import datetime
import uuid

# Initialize Celery
celery_app = Celery(
    "genai_file_search",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

@celery_app.task(bind=True, name="process_file")
def process_file_task(self, file_id: int):
    """
    Async task to process uploaded file
    
    Args:
        file_id: Database file ID
    
    Returns:
        Processing result
    """
    db = SessionLocal()
    
    try:
        # Get file from database
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            return {"status": "error", "message": "File not found"}
        
        # Update status
        file.status = "processing"
        db.commit()
        
        logger.info(f"Processing file: {file.original_filename} (ID: {file_id})")
        
        # Step 1: Extract text from file
        documents = file_processor.process_file(file.file_path, file.file_type)
        
        if not documents:
            file.status = "failed"
            file.error_message = "No text extracted from file"
            db.commit()
            return {"status": "error", "message": "No text extracted"}
        
        logger.info(f"Extracted {len(documents)} documents from file")
        
        # Step 2: Chunk documents
        all_chunks = []
        for doc in documents:
            chunks = chunking_service.chunk_text(
                doc["text"],
                metadata=doc.get("metadata", {})
            )
            all_chunks.extend(chunks)
        
        if not all_chunks:
            file.status = "failed"
            file.error_message = "No chunks created"
            db.commit()
            return {"status": "error", "message": "No chunks created"}
        
        logger.info(f"Created {len(all_chunks)} chunks")
        
        # Step 3: Generate embeddings
        chunk_texts = [chunk["text"] for chunk in all_chunks]
        embeddings = embeddings_service.generate_embeddings_batch(chunk_texts)
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Step 4: Store in database and vector store
        chunk_ids = []
        chunk_metadatas = []
        
        for idx, chunk in enumerate(all_chunks):
            # Generate unique chunk ID
            chunk_id = f"file_{file_id}_chunk_{idx}_{uuid.uuid4().hex[:8]}"
            chunk_ids.append(chunk_id)
            
            # Create chunk in database
            db_chunk = Chunk(
                file_id=file_id,
                chunk_id=chunk_id,
                chunk_text=chunk["text"],
                chunk_index=idx,
                page_number=chunk.get("page_number")
            )
            db.add(db_chunk)
            
            # Prepare metadata for vector store
            metadata = {
                "file_id": file_id,
                "category_id": file.category_id,
                "chunk_index": idx,
                "page_number": chunk.get("page_number", 0)
            }
            chunk_metadatas.append(metadata)
        
        # Commit chunks to database
        db.commit()
        
        # Step 5: Add to vector store
        success = vector_store_service.add_chunks(
            chunk_ids=chunk_ids,
            texts=chunk_texts,
            embeddings=embeddings,
            metadatas=chunk_metadatas
        )
        
        if not success:
            file.status = "failed"
            file.error_message = "Failed to add to vector store"
            db.commit()
            return {"status": "error", "message": "Failed to add to vector store"}
        
        # Update file status
        file.status = "completed"
        file.total_chunks = len(all_chunks)
        file.processed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully processed file {file_id} with {len(all_chunks)} chunks")
        
        return {
            "status": "success",
            "file_id": file_id,
            "total_chunks": len(all_chunks)
        }
        
    except Exception as e:
        logger.error(f"Error processing file {file_id}: {e}")
        
        # Update file status
        file = db.query(File).filter(File.id == file_id).first()
        if file:
            file.status = "failed"
            file.error_message = str(e)
            db.commit()
        
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()
