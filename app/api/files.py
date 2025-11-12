from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, Form
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from app.database import get_db
from app.models import Category, File
from app.schemas import FileUploadResponse, FileStatusResponse, FileListResponse, TaskStatusResponse
from app.config import settings
from app.tasks.celery_tasks import process_file_task, celery_app
from app.services.vector_store import vector_store_service
from loguru import logger
import uuid

router = APIRouter(prefix="/api/files", tags=["Files"])

ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.csv',
    '.jpg', '.jpeg', '.png', '.bmp', '.tiff',
    '.ppt', '.pptx', '.json', '.sql', '.xml'
}

def validate_file(file: UploadFile) -> str:
    """Validate file type and size"""
    # Get file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    return file_ext

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    category_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Upload a file for processing"""
    
    # Validate category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Validate file
    file_ext = validate_file(file)
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="Error saving file")
    
    # Create database entry
    db_file = File(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_type=file_ext,
        file_size=file_size,
        category_id=category_id,
        status="pending"
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    # Start async processing
    task = process_file_task.apply_async(args=[db_file.id])
    
    # Update task ID
    db_file.task_id = task.id
    db.commit()
    
    logger.info(f"File uploaded: {file.filename} (ID: {db_file.id}, Task: {task.id})")
    
    return FileUploadResponse(
        file_id=db_file.id,
        filename=file.filename,
        task_id=task.id,
        status="pending",
        message="File uploaded successfully. Processing started."
    )

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Get status of file processing task"""
    
    task = celery_app.AsyncResult(task_id)
    
    response = TaskStatusResponse(
        task_id=task_id,
        status=task.state,
        result=None,
        error=None
    )
    
    if task.state == "SUCCESS":
        response.result = task.result
    elif task.state == "FAILURE":
        response.error = str(task.info)
    
    return response

@router.get("/list", response_model=List[FileListResponse])
def list_files(category_id: int = None, db: Session = Depends(get_db)):
    """List all files, optionally filtered by category"""
    
    query = db.query(File)
    if category_id:
        query = query.filter(File.category_id == category_id)
    
    files = query.all()
    
    result = []
    for file in files:
        result.append(FileListResponse(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            file_type=file.file_type,
            file_size=file.file_size,
            category_id=file.category_id,
            category_name=file.category.name,
            status=file.status,
            total_chunks=file.total_chunks,
            created_at=file.created_at
        ))
    
    return result

@router.get("/{file_id}", response_model=FileStatusResponse)
def get_file_status(file_id: int, db: Session = Depends(get_db)):
    """Get file processing status"""
    
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileStatusResponse(
        file_id=file.id,
        filename=file.original_filename,
        status=file.status,
        total_chunks=file.total_chunks,
        error_message=file.error_message,
        processed_at=file.processed_at
    )

@router.delete("/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    """Delete a file"""
    
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete from vector store
    vector_store_service.delete_by_file_id(file_id)
    
    # Delete physical file
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    # Delete from database (cascades to chunks)
    db.delete(file)
    db.commit()
    
    logger.info(f"Deleted file: {file.original_filename} (ID: {file_id})")
    
    return {"message": "File deleted successfully", "file_id": file_id}
