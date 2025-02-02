from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.utills.auth import get_current_user
from ..database import get_db
from ..models import ModelRateLimit, User
from pydantic import BaseModel

router = APIRouter()

# Pydantic model for creating and updating rate limits
class ModelRateLimitCreate(BaseModel):
    model_id: str
    model_type: str
    requests_per_minute: int
    requests_per_day: int
    tokens_per_minute: int = None
    tokens_per_day: int = None
    audio_seconds_per_hour: int = None
    audio_seconds_per_day: int = None
    class Config:
        protected_namespaces = ()

class ModelRateLimitResponse(ModelRateLimitCreate):
    id: int

@router.post("/model-rate-limit/", response_model=ModelRateLimitResponse)
def create_model_rate_limit(rate_limit: ModelRateLimitCreate,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_rate_limit = db.query(ModelRateLimit).filter(ModelRateLimit.model_id == rate_limit.model_id).first()
    if db_rate_limit:
        raise HTTPException(status_code=400, detail="Model ID already registered")
    new_rate_limit = ModelRateLimit(**rate_limit.dict())
    db.add(new_rate_limit)
    db.commit()
    db.refresh(new_rate_limit)
    return new_rate_limit

@router.get("/model-rate-limit")
def read_model_rate_limit( current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    rate_limit = db.query(ModelRateLimit).all()
    if rate_limit is None:
        raise HTTPException(status_code=404, detail="Model rate limit not found")
    return rate_limit

# @router.get("/model-rate-limit/{model_id}", response_model=ModelRateLimitResponse)
# def read_model_rate_limit(model_id: str, db: Session = Depends(get_db)):
#     rate_limit = db.query(ModelRateLimit).filter(ModelRateLimit.model_id == model_id).first()
#     if rate_limit is None:
#         raise HTTPException(status_code=404, detail="Model rate limit not found")
#     return rate_limit

@router.put("/model-rate-limit", response_model=ModelRateLimitResponse)
def update_model_rate_limit(model_id: str, rate_limit: ModelRateLimitCreate,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_rate_limit = db.query(ModelRateLimit).filter(ModelRateLimit.model_id == model_id).first()
    if db_rate_limit is None:
        raise HTTPException(status_code=404, detail="Model rate limit not found")
    
    for key, value in rate_limit.dict().items():
        setattr(db_rate_limit, key, value)
    
    db.commit()
    db.refresh(db_rate_limit)
    return db_rate_limit

@router.delete("/model-rate-limit", response_model=ModelRateLimitResponse)
def delete_model_rate_limit(model_id: str,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_rate_limit = db.query(ModelRateLimit).filter(ModelRateLimit.model_id == model_id).first()
    if db_rate_limit is None:
        raise HTTPException(status_code=404, detail="Model rate limit not found")
    
    db.delete(db_rate_limit)
    db.commit()
    return db_rate_limit
