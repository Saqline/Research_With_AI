
from functools import wraps
from passlib.context import CryptContext
from datetime import datetime, timedelta
import string
from typing import List, Optional
from app.database import get_db
from fastapi import  HTTPException, Depends
from sqlalchemy.orm import sessionmaker, Session, relationship
from fastapi import status
from jose import JWTError, jwt
from datetime import datetime, timedelta

from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random

from sqlalchemy import func

from app.models import User




# Password encryption context

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token handling
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None, db_session: Session = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta if expires_delta else datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    user_id = data["user_id"]
    user = db_session.query(User).filter(User.id == user_id).first()
    user.access_token = encoded_jwt
    db_session.commit()
    return encoded_jwt
    

# Define OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        print("Token:",token)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        if user.access_token != token:
            raise HTTPException(status_code=400, detail="Your token does not match with the one stored in the database.")
        return user     
    except JWTError:
        raise credentials_exception

# def role_required(roles: List[str]):
#     def role_checker(current_user: User = Depends(get_current_user)):
#         if current_user.role not in roles:
#             raise HTTPException(status_code=403, detail="Forbidden")
#         return current_user
#     return role_checker

# Role Checker Decorator
# Role Checker Decorator for FastAPI
def role_required(role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if current_user is None:
                raise HTTPException(status_code=401, detail="Invalid user")
            if current_user.role != role:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail=f'Access restricted to db role {current_user.role}  {role} users')
            return fn(*args, **kwargs)
        return wrapper
    return decorator



def role_required(roles: List[str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not isinstance(current_user, User):
                raise HTTPException(status_code=500, detail="Internal server error: User is not resolved.")
            if current_user.role not in roles:
                raise HTTPException(status_code=403, detail="Forbidden: You don't have access.")
            return await func(*args, **kwargs, current_user=current_user)  # Pass current_user to the endpoint
        return wrapper
    return decorator

def generate_six_digit_code():
    chars = string.ascii_uppercase + string.digits 
    random_sys = random.SystemRandom()
    return ''.join(random_sys.choice(chars) for _ in range(6))


def generate_code_and_expiry():
    code = generate_six_digit_code()
    expiry = datetime.utcnow() + timedelta(minutes=5)
    return code, expiry

