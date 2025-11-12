from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Category, File
from app.schemas import CategoryCreate, CategoryResponse
from app.services.vector_store import vector_store_service
from loguru import logger

router = APIRouter(prefix="/api/categories", tags=["Categories"])

@router.post("/create", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category"""
    
    # Check if category already exists
    existing = db.query(Category).filter(Category.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    # Create category
    db_category = Category(
        name=category.name,
        description=category.description
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    logger.info(f"Created category: {category.name} (ID: {db_category.id})")
    
    # Get file count
    file_count = db.query(File).filter(File.category_id == db_category.id).count()
    
    return CategoryResponse(
        id=db_category.id,
        name=db_category.name,
        description=db_category.description,
        created_at=db_category.created_at,
        file_count=file_count
    )

@router.get("/list", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """List all categories"""
    
    categories = db.query(Category).all()
    
    result = []
    for cat in categories:
        file_count = db.query(File).filter(File.category_id == cat.id).count()
        result.append(CategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            created_at=cat.created_at,
            file_count=file_count
        ))
    
    return result

@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get category by ID"""
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    file_count = db.query(File).filter(File.category_id == category.id).count()
    
    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        created_at=category.created_at,
        file_count=file_count
    )

@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a category and all its files"""
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Delete from vector store
    vector_store_service.delete_by_category_id(category_id)
    
    # Delete category (cascades to files and chunks)
    db.delete(category)
    db.commit()
    
    logger.info(f"Deleted category: {category.name} (ID: {category_id})")
    
    return {"message": "Category deleted successfully", "category_id": category_id}
