import uuid
from sqlalchemy.orm import sessionmaker, Session, relationship
from fastapi import APIRouter, Depends, HTTPException,status
from pydantic import BaseModel

from app.models import APIKey, User
from app.database import get_db
from app.utills.auth import get_current_user



router = APIRouter()

class APIKeyCreateRequest(BaseModel):
    name: str

@router.post("/generate-api-key")
def generate_api_key(
    api_key_data: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    api_key_count = db.query(APIKey).filter(APIKey.user_id == current_user.id).count()

    if current_user.role == "customer":
        api_key_count = db.query(APIKey).filter(APIKey.user_id == current_user.id).count()

        if api_key_count >= 5:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key creation limit reached. You cannot generate more than 5 API keys.")
    
    existing_key = db.query(APIKey).filter(
        APIKey.name == api_key_data.name,
        APIKey.user_id == current_user.id
    ).first()

    if existing_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key name must be unique for the current user")

    key = str(uuid.uuid4())
    db_key = APIKey(key=key, name=api_key_data.name, user_id=current_user.id)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    
    return {"api_key": db_key.key, "status": "active", "name": db_key.name}
# Disable an API key
@router.post("/toggle-api-key")
def toggle_api_key(api_key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.user_id == current_user.id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    db_key.status = not db_key.status  
    db.commit()
    if db_key.status:
        return {"message": "API key enabled"}
    else:
        return {"message": "API key disabled"}

@router.post("/delete-api-key")
def delete_api_key(api_key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.user_id == current_user.id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(db_key)
    db.commit()
    return {"message": "API key deleted"}


# Get all API keys for the current user
@router.get("/api-keys")
def get_api_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    return {"api_keys": [{"key": key.key, "name": key.name,"created_at": key.created_at, "status": "active" if key.status else "disabled"} for key in keys]}

# Get all API keys
@router.get("/api-keys-all")
def get_api_keys(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    keys = db.query(APIKey).all()
    return {"api_keys": [{"key": key.key, "created_at": key.created_at, "status": "active" if key.status else "disabled"} for key in keys]}

