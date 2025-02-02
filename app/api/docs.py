from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.models import API_Documentation, User
from app.schemas import APIDocumentationCreate, APIDocumentationUpdate
from app.utills.auth import get_current_user



router = APIRouter()


@router.post("/documentation/")
def create_documentation_endpoint(doc: APIDocumentationCreate,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_documentation(db=db, doc=doc)

@router.get("/documentation/{doc_id}")
def read_documentation(doc_id: int, current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    result = db.query(API_Documentation).filter(API_Documentation.id == doc_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="API Documentation not found")
    return result

@router.get("/documentation/")
def read_all_documentation(skip: int = 0, limit: int = 10, 
                           title: Optional[str] = None, section: Optional[str] = None, 
                           sort_field: Optional[str] = None, sort_order: Optional[str] = None,current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    return get_all_documentation(db, skip, limit, title, section, sort_field, sort_order)

@router.put("/documentation/{doc_id}")
def update_documentation_endpoint(doc_id: int, doc: APIDocumentationUpdate,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    updated_doc = update_documentation(db=db, doc_id=doc_id, doc_update=doc)
    if updated_doc is None:
        raise HTTPException(status_code=404, detail="Documentation not found")
    return updated_doc

@router.delete("/documentation/{doc_id}")
def delete_documentation_endpoint(doc_id: int,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deleted_doc = delete_documentation(db, doc_id)
    if deleted_doc is None:
        raise HTTPException(status_code=404, detail="Documentation not found")
    return deleted_doc


##api doc
def create_documentation(db: Session, doc: APIDocumentationCreate,current_user: User = Depends(get_current_user)):
    db_doc = API_Documentation(
        title=doc.title,
        section=doc.section,
        content=doc.content,
        example_code=doc.example_code
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc




def get_all_documentation(db: Session, skip: int = 0, limit: int = 10, 
                           title: Optional[str] = None, section: Optional[str] = None, 
                           sort_field: Optional[str] = None, sort_order: Optional[str] = None,current_user: User = Depends(get_current_user)):
    query = db.query(API_Documentation)
    
    if title:
        query = query.filter(API_Documentation.title.like(f"%{title}%"))
    
    if section:
        query = query.filter(API_Documentation.section.like(f"%{section}%"))
    
    if sort_field and sort_order:
        if sort_order.lower() == "asc":
            query = query.order_by(getattr(API_Documentation, sort_field).asc())
        elif sort_order.lower() == "desc":
            query = query.order_by(getattr(API_Documentation, sort_field).desc())
        else:
            raise HTTPException(status_code=400, detail="Invalid sort order. Use 'asc' or 'desc'.")
    
    query = query.offset(skip).limit(limit)
    
    return query.all()

def update_documentation(db: Session, doc_id: int, doc_update: APIDocumentationCreate,current_user: User = Depends(get_current_user),):
    db_doc = db.query(API_Documentation).filter(API_Documentation.id == doc_id).first()
    if db_doc:
        db_doc.title = doc_update.title
        db_doc.section = doc_update.section
        db_doc.content = doc_update.content
        db_doc.example_code = doc_update.example_code
        db.commit()
        db.refresh(db_doc)
        return db_doc
    return None

def delete_documentation(db: Session, doc_id: int,current_user: User = Depends(get_current_user),):
    db_doc = db.query(API_Documentation).filter(API_Documentation.id == doc_id).first()
    if db_doc:
        db.delete(db_doc)
        db.commit()
        return db_doc
    return None

