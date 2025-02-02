from datetime import datetime, timedelta
from typing import List
from fastapi import Depends
from celery import Celery
from celery.schedules import crontab
from app.models import Payment, User
from sqlalchemy.orm import sessionmaker, Session, relationship

from app.database import get_db
from python.app.utills.email import send_email
app = Celery()
from datetime import datetime, timedelta
 
@app.task
def downgrade_users(db: Session = Depends(get_db)):
    # Get all users with a paid role
    users: List[User] = db.query(User).filter(User.role.in_(["general_paid", "advance_user"])).all()

    # Calculate the date 30 days ago
    thirty_days_ago = datetime.now() - timedelta(days=30)

    # Check if each user has made a payment in the last 30 days
    for user in users:
        payments: List[Payment] = db.query(Payment).filter(Payment.user_id == user.id).filter(Payment.payment_date >= thirty_days_ago).all()
        if not payments:
            # Calculate the date 2 days before the 30-day mark
            two_days_before_thirty_days_ago = thirty_days_ago + timedelta(days=2)

            # Check if the user has made a payment in the last 2 days before the 30-day mark
            recent_payments: List[Payment] = db.query(Payment).filter(Payment.user_id == user.id).filter(Payment.payment_date >= two_days_before_thirty_days_ago).all()
            if recent_payments:
                # Send a reminder email to the user
                send_email(user.email, "Payment Reminder", "Please make your payment as soon as possible. If you have already made a payment, please ignore this email.")
            else:
                # Downgrade the user to a general user
                user.role = "customer"
                db.commit()
                db.refresh(user)


app.conf.beat_schedule = {
    'downgrade-users': {
        'task': 'downgrade_users',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2am
    },
}