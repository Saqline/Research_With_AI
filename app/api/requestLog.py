
from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy import func

from app.models import APIKey, RequestLog, User
from app.database import get_db
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
from app.utills.auth import get_current_user

router = APIRouter()
@router.get("/request-logs-all")
def get_all_request_logs(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    # Retrieve all request logs
    logs = db.query(RequestLog).all()
    
    # Format the logs for response
    return {"request_logs": [
        {"id": log.id, "api_key": log.api_key, "query": log.query, "timestamp": log.timestamp} 
        for log in logs
    ]}
# Get all request logs by api key
@router.get("/request-logs-by-apikey")
def get_request_logs(api_key: str, current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    # Check if API key exists
    db_key = db.query(APIKey).filter(APIKey.key == api_key).first()
    if not db_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    logs = db.query(RequestLog).filter(RequestLog.api_key == api_key).all()
    return {"total_logs": len(logs),"request_logs": [{"id": log.id, "query": log.query, "timestamp": log.timestamp} for log in logs]}

# Get all request logs for the current user's API keys
@router.get("/request-logs-current-user")
def get_request_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    api_keys = [key.key for key in keys]
    logs = db.query(RequestLog).filter(RequestLog.api_key.in_(api_keys)).all()
    return {"request_logs": [{"id": log.id, "api_key": log.api_key, "query": log.query, "timestamp": log.timestamp} for log in logs]}


@router.get("/request-logs-current-user_month")
def get_request_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Get current date and month
    today = datetime.today()
    current_month = today.month
    current_year = today.year

    # Get API keys for current user
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    api_keys = [key.key for key in keys]

    # Get request logs for current user and month
    logs = db.query(RequestLog).filter(RequestLog.api_key.in_(api_keys)).filter(
        func.extract('month', RequestLog.timestamp) == current_month,
        func.extract('year', RequestLog.timestamp) == current_year
    ).all()

    # Group logs by day and count
    log_counts = {}
    for log in logs:
        log_date = log.timestamp.date()
        log_counts[log_date] = log_counts.get(log_date, 0) + 1

    # Create array of log counts for each day of the month
    month_log_counts = []
    for day in range(1, today.day + 1):
        log_date = datetime(current_year, current_month, day).date()
        log_count = log_counts.get(log_date, 0)
        month_log_counts.append({"date": log_date.strftime("%d-%m-%Y"), "count": log_count})

    return {"request_logs": month_log_counts}