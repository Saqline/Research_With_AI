from sqlalchemy import JSON, Column, Integer, String, Boolean, DateTime, ForeignKey, Text,Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base  

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False) 
    email = Column(String(255), unique=True, index=True, nullable=False)
    city = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(String(50), default="customer", nullable=False)
    email_verified = Column(Boolean, default=False)
    ev_code = Column(String(6), nullable=True)
    ev_code_expire = Column(DateTime, nullable=True)
    fp_code = Column(String(6), nullable=True)
    fp_code_expire = Column(DateTime, nullable=True)
    access_token = Column(String(255), nullable=True)
    register_type = Column(String(55), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow) 
    register_ip = Column(String(45), nullable=True) 
    login_ip = Column(String(45), nullable=True) 

    # Relationship with the Plan table
    plans = relationship("UserPlan", back_populates="user")
    payments = relationship("Payment", back_populates="user")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)  
    api_calls = Column(Integer, nullable=False)  
    price = Column(Float, nullable=False)  
    validity_days = Column(Integer, nullable=False)  

class UserPlan(Base):
    __tablename__ = "user_plan"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  
    plan_name = Column(String(255), nullable=False)
    plan_buy_start_date = Column(DateTime, nullable=False)
    plan_expire_date = Column(DateTime, nullable=False)
    remain_request = Column(Integer, default=1000)  
    total_request = Column(Integer, default=1000)  
    plan_status = Column(Boolean, default=True)  
    
    user = relationship("User", back_populates="plans")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Integer, nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)
    payment_type = Column(String(50), nullable=False)
    invoice_number = Column(String(255), nullable=False)  
    payment_method = Column(String(50), nullable=False) 
    status = Column(String(50), default="completed", nullable=False)
    user = relationship("User", back_populates="payments")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    key = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User")

class RequestLog(Base):
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(50), index=True)
    query = Column(String(1024), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    model_id = Column(String(255), ForeignKey('model_rate_limits.model_id'), nullable=True)
    model = relationship("ModelRateLimit")

class API_Documentation(Base):
    __tablename__ = "api_documentation"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    section = Column(String(50), nullable=False)
    content = Column(Text(), nullable=False)
    example_code = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelRateLimit(Base):
    __tablename__ = "model_rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(255), unique=True, index=True)  
    model_type = Column(String(50), nullable=False)  
    requests_per_minute = Column(Integer, nullable=False)
    requests_per_day = Column(Integer, nullable=False)
    tokens_per_minute = Column(Integer, nullable=True)
    tokens_per_day = Column(Integer, nullable=True)
    audio_seconds_per_hour = Column(Integer, nullable=True)  
    audio_seconds_per_day = Column(Integer, nullable=True) 





