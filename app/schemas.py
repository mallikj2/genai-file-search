from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Category Schemas
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    file_count: int = 0
    
    class Config:
        from_attributes = True

# File Schemas
class FileUploadResponse(BaseModel):
    file_id: int
    filename: str
    task_id: str
    status: str
    message: str

class FileStatusResponse(BaseModel):
    file_id: int
    filename: str
    status: str
    total_chunks: int
    error_message: Optional[str]
    processed_at: Optional[datetime]

class FileListResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    category_id: int
    category_name: str
    status: str
    total_chunks: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Search Schemas
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    category_id: int
    top_k: int = Field(default=5, ge=1, le=20)

class SearchResult(BaseModel):
    chunk_id: str
    text: str
    confidence_score: float

class SearchResponse(BaseModel):
    answer: str
    confidence_score: float
    results: List[SearchResult] = []

class SummarizeRequest(BaseModel):
    category_id: int
    max_length: Optional[int] = Field(default=500, ge=100, le=2000)

class SummarizeResponse(BaseModel):
    summary: str
    confidence_score: float

class QARequest(BaseModel):
    question: str = Field(..., min_length=1)
    category_id: int
    top_k: int = Field(default=5, ge=1, le=20)

class QAResponse(BaseModel):
    answer: str
    confidence_score: float
    relevant_chunks: List[SearchResult] = []

class FindPassagesRequest(BaseModel):
    query: str = Field(..., min_length=1)
    category_id: int
    top_k: int = Field(default=10, ge=1, le=50)

class FindPassagesResponse(BaseModel):
    passages: List[SearchResult]
    total_found: int

# Task Status Schema
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
