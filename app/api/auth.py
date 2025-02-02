import string
from typing import List, Optional
from app.utills.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, generate_code_and_expiry, get_current_user, get_password_hash, role_required, verify_password
from app.utills.email import send_email
from ..models import  Payment, Plan,  User, UserPlan
from app.database import get_db
from ..schemas import  SignInSchema, UserCreateRequest
from fastapi import FastAPI, HTTPException, Depends
from fastapi import BackgroundTasks
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import  Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from fastapi import APIRouter
import asyncio
from app.utills.email import send_verification_email 
from fastapi import Request



router = APIRouter()

@router.post("/register-customer")
def register_customer(
    data: UserCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(data.password)
    ev_code, ev_code_expire = generate_code_and_expiry()
    # Get client IP address
    client_ip = request.client.host
    user = User(
        name=data.name,
        email=data.email,
        city=data.city,
        hashed_password=hashed_password,
        role="customer",
        email_verified=False,
        ev_code=ev_code,
        ev_code_expire=ev_code_expire,
        register_type="general",
        register_ip=client_ip  # Save the registration IP
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send verification email in the background
    background_tasks.add_task(send_verification_email, user.email, ev_code)

    return {"message": "Customer registered successfully. Please check your email for verification."}

@router.post("/signin")
def login_user(sign_in_data: SignInSchema ,
               request: Request,
               background_tasks: BackgroundTasks ,
               db: Session = Depends(get_db)):
    print(sign_in_data.email, sign_in_data.password)
    user = db.query(User).filter(User.email == sign_in_data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    
    if not verify_password(sign_in_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Username and Password not match!")
    
    if not user.email_verified:
        ev_code, ev_code_expire = generate_code_and_expiry()
        user.ev_code = ev_code
        user.ev_code_expire = ev_code_expire
        db.commit()

        
        background_tasks.add_task(send_verification_email, user.email, user.ev_code)

        raise HTTPException(status_code=400, detail="Email not verified. A new verification code has been sent to your email.")
    
    user_plan = db.query(UserPlan).filter(UserPlan.user_id == user.id).first()
    if user_plan and user_plan.plan_expire_date < datetime.now():
        user_plan.plan_name = "Explorer"
        user_plan.plan_buy_start_date = datetime.now()
        user_plan.plan_expire_date = datetime.now() + timedelta(days=30)
        user_plan.remain_request = 1200
        user_plan.total_request = 1200
        db.commit()
        
    client_ip = request.client.host
    user.login_ip = client_ip  
    db.commit()
    access_token = create_access_token(data={"user_id": str(user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),db_session=db)
    return {"access_token": access_token, "token_type": "Bearer","user_id":user.id}


@router.post("/google-sign")
def register_customer(
    data: UserCreateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        user_plan = db.query(UserPlan).filter(UserPlan.user_id == existing_user.id).first()
        if user_plan and user_plan.plan_expire_date < datetime.now():
            user_plan.plan_name = "Explorer"
            user_plan.plan_buy_start_date = datetime.now()
            user_plan.plan_expire_date = datetime.now() + timedelta(days=30)
            user_plan.remain_request = 1200
            user_plan.total_request = 1200
            db.commit()
        access_token = create_access_token(data={"user_id": str(existing_user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), db_session=db)

        return {"message": "ok", "access_token": access_token, "user_id": existing_user.id}
    client_ip = request.client.host
   
    user = User(
        name=data.name,
        email=data.email,
        city=data.city,
        hashed_password=None,
        role="customer",
        email_verified=True,  
        ev_code=None,  
        ev_code_expire=None,  
        register_type="google",
        register_ip=client_ip  
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    explorer_plan = db.query(Plan).filter(Plan.name == "Explorer").first()

    if not explorer_plan:
        raise HTTPException(status_code=404, detail="Explorer plan not found")

    new_user_plan = UserPlan(
        user_id=user.id,
        plan_name=explorer_plan.name,
        plan_buy_start_date=datetime.utcnow(),
        plan_expire_date=datetime.utcnow() + timedelta(days=explorer_plan.validity_days),
        remain_request=explorer_plan.api_calls,
        total_request=explorer_plan.api_calls,
        plan_status=True
    )
    db.add(new_user_plan)
    db.commit()
    access_token = create_access_token(data={"user_id": str(user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), db_session=db)

    return {"message": "ok", "access_token": access_token,"user_id":user.id}

# Register as Admin
@router.post("/register-admin")
def register_admin(data: UserCreateRequest, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(data.password)
    user = User(
        name=data.name,
        email=data.email,
        city=data.city,
        hashed_password=hashed_password,
        email_verified=True,
        role="admin"  
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Admin registered successfully"}


@router.post("/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print(form_data.username,form_data.password)
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Username and Password not match!")
    
    if not user.email_verified:
        ev_code, ev_code_expire = generate_code_and_expiry()
        user.ev_code = ev_code
        user.ev_code_expire = ev_code_expire
        db.commit()

        # Send the verification email
        #background_tasks.add_task(send_verification_email, user.email, user.ev_code)

        raise HTTPException(status_code=400, detail="Email not verified. A new verification code has been sent to your email.")
    
    access_token = create_access_token(data={"user_id": str(user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),db_session=db)
    return {"access_token": access_token, "token_type": "Bearer","user_id":user.id}




class EmailSchema(BaseModel):
    gmail: str
@router.post("/send-verification-email")
def verification_email(
    email_data: EmailSchema,  # Use schema for input validation
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email_data.gmail).first()

    if not user:
        raise HTTPException(status_code=400, detail="User with this email does not exist")

    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")

    ev_code, ev_code_expire = generate_code_and_expiry()

    user.ev_code = ev_code
    user.ev_code_expire = ev_code_expire
    db.commit()

    background_tasks.add_task(send_verification_email, email_data.gmail, ev_code)

    return {"message": "Verification code sent to email"}

class VerifyEmailRequest(BaseModel):
    email: str
    ev_code: str
@router.post("/verify-email")
def verify_email(data: VerifyEmailRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=400, detail="User with this email does not exist")

    if user.ev_code != data.ev_code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    if user.ev_code_expire < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification code has expired")

    user.email_verified = True
    user.ev_code = None  
    user.ev_code_expire = None  
    db.commit()
    explorer_plan = db.query(Plan).filter(Plan.name == "Explorer").first()

    if not explorer_plan:
        raise HTTPException(status_code=404, detail="Explorer plan not found")

    new_user_plan = UserPlan(
        user_id=user.id,
        plan_name=explorer_plan.name,
        plan_buy_start_date=datetime.utcnow(),
        plan_expire_date=datetime.utcnow() + timedelta(days=explorer_plan.validity_days),
        remain_request=explorer_plan.api_calls,
        total_request=explorer_plan.api_calls,
        plan_status=True
    )
    db.add(new_user_plan)
    db.commit()
    access_token = create_access_token(data={"user_id": str(user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),db_session=db)

    return {"message": "Email verified successfully", "access_token": access_token,"user_id":user.id}


class ForgotPasswordRequest(BaseModel):
    email: str
@router.post("/send-forgot-password-otp")
def send_forgot_password_otp(data: ForgotPasswordRequest,background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=400, detail="User with this email does not exist")

    fp_code, fp_code_expire = generate_code_and_expiry()

    user.fp_code = fp_code
    user.fp_code_expire = fp_code_expire 
    db.commit()

    background_tasks.add_task(send_verification_email, data.email, fp_code)

    return {"message": "Forgot password code sent to email"}

class ResetPasswordSchema(BaseModel):
    email: str
    fp_code: str
    new_password: str
@router.post("/reset-password")
def reset_password(
    reset_data: ResetPasswordSchema,  
    background_tasks: BackgroundTasks,  
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == reset_data.email).first()

    if not user:
        raise HTTPException(status_code=400, detail="User with this email does not exist")

    if user.fp_code != reset_data.fp_code:
        raise HTTPException(status_code=400, detail="Invalid forgot password code")

    if user.fp_code_expire < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Forgot password code has expired")

    hashed_password = get_password_hash(reset_data.new_password)
    user.hashed_password = hashed_password
    user.fp_code = None  
    user.fp_code_expire = None  
    db.commit()

    # Add background task to send email
    #background_tasks.add_task(send_reset_email, reset_data.gmail)

    return {"message": "Password reset successfully"}




@router.get("/user/me")
async def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user



@router.post("/admin-only", response_model=None)
@role_required(["admin"])
async def admin_only_endpoint(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "name": current_user.name, "role": current_user.role}



class UpgradeToPaidRequest(BaseModel):
    user_id: int

@router.post("/upgrade-to-paid_current_user")
def upgrade_to_paid(amount: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != "customer":
        raise HTTPException(status_code=400, detail="User is not a customer or already upgraded")

    if amount == 500:
        current_user.role = "general_paid"
    elif amount == 1000:
        current_user.role = "advance_user"
    else:
        raise HTTPException(status_code=400, detail="Invalid amount")

    db.commit()
    db.refresh(current_user)

    payment = Payment(
        user_id=current_user.id,
        amount=amount,
        payment_type="subscription",
        status="completed"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {"message": "User role updated", "user_id": current_user.id, "new_role": current_user.role, "payment_id": payment.id}



class EmailSchema(BaseModel):
    email: str
    name: str
    details: str

@router.post("/user/contactus/")
def send_email_endpoint(email_schema: EmailSchema): 
    subject = "Email From - " + email_schema.email
    body ="Name: " + email_schema.name + "\n" + "Email: " + email_schema.email+ "\n" + "Details: " + email_schema.details
    email = "mesobjanta@gmail.com"
    send_email(email, subject, body)
    email = "info@sobjanta.ai"
    send_email(email, subject, body)
    email = "mdallmamunridoy@gmail.com"
    send_email(email, subject, body)
    email = "ahmedul@techknowgram.com"
    send_email(email, subject, body)
    return {"message": "Email sent successfully"}





