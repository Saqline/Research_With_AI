from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session

from pydantic import BaseModel

from app.database import get_db
from app.models import Payment, Plan, User, UserPlan
from app.utills.auth import get_current_user, role_required

router = APIRouter()

class PlanCreateRequest(BaseModel):
    name: str
    api_calls: int
    price: float
    validity_days: int


@router.get("/plans")
@role_required(["admin"])
def list_plans(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    plans = db.query(Plan).all()
    return plans

@router.post("/plans")
@role_required(["admin"])
def create_plan(plan_request: PlanCreateRequest,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if the plan already exists
    existing_plan = db.query(Plan).filter(Plan.name == plan_request.name).first()
    if existing_plan:
        raise HTTPException(status_code=400, detail="Plan with this name already exists")

    # Create the new plan
    new_plan = Plan(
        name=plan_request.name,
        api_calls=plan_request.api_calls,
        price=plan_request.price,
        validity_days=plan_request.validity_days
    )
    db.add(new_plan)
    db.commit()

    return {"message": "Plan created successfully"}

@router.put("/plans/{plan_id}")
@role_required(["admin"])
def update_plan(plan_id: int, plan_request: PlanCreateRequest,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.name = plan_request.name
    plan.api_calls = plan_request.api_calls
    plan.price = plan_request.price
    plan.validity_days = plan_request.validity_days

    db.commit()

    return {"message": "Plan updated successfully"}



@router.post("/change-user-plan/{plan_name}")
def change_plan(plan_name: str, invoice_number: str, payment_method: str, payment_type: str, user_id: int, db: Session = Depends(get_db)):
    print("in Change user Token details:  ",user_id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    selected_plan = db.query(Plan).filter(Plan.name == plan_name).first()
    if not selected_plan:
        raise HTTPException(status_code=400, detail="Invalid plan selected")

    current_user_plan = db.query(UserPlan).filter(UserPlan.user_id == user_id).first()

    if current_user_plan:
        current_user_plan.plan_name = selected_plan.name
        current_user_plan.plan_buy_start_date = datetime.now()
        current_user_plan.plan_expire_date = datetime.now() + timedelta(days=selected_plan.validity_days)
        current_user_plan.remain_request += selected_plan.api_calls
        current_user_plan.total_request += selected_plan.api_calls
        db.commit()
    else:
        new_user_plan = UserPlan(
            user_id=user_id,
            plan_name=selected_plan.name,
            plan_buy_start_date=datetime.now(),
            plan_expire_date=datetime.now() + timedelta(days=selected_plan.validity_days),
            remain_request=selected_plan.api_calls,
            total_request=selected_plan.api_calls
        )
        db.add(new_user_plan)
        db.commit()

    new_payment = Payment(
        user_id=user.id,
        amount=selected_plan.price,
        payment_method=payment_method,
        invoice_number=invoice_number,
        payment_type=payment_type,
        payment_date=datetime.utcnow(),
        status="completed"  # Assuming payment was successful
    )
    db.add(new_payment)
    db.commit()

    return {"message": f"Plan changed to {selected_plan.name} successfully"}

@router.post("/change-user-plan-by-admin/{plan_name}")
@role_required(["admin"])
def change_plan(plan_name: str, user_id: int,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if the user exists
    print("in ",current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get the plan details
    selected_plan = None
    # Get the plan details
    selected_plan = db.query(Plan).filter(Plan.name == plan_name).first()

    if not selected_plan:
        raise HTTPException(status_code=400, detail="Invalid plan selected")
    
    # Get the user's current plan
    current_user_plan = db.query(UserPlan).filter(UserPlan.user_id == user_id).first()

    if current_user_plan:
        # Update the user's current plan
        current_user_plan.id = selected_plan.id
        current_user_plan.plan_buy_start_date = datetime.now()
        current_user_plan.plan_expire_date = datetime.now() + timedelta(days=selected_plan.validity_days)
        current_user_plan.remain_request = selected_plan.api_calls
        current_user_plan.total_request = selected_plan.api_calls
        db.commit()
    else:
        # Create a new user plan
        new_user_plan = UserPlan(
            user_id=user_id,
            plan_id=selected_plan.id,
            plan_buy_start_date=datetime.now(),
            plan_expire_date=datetime.now() + timedelta(days=selected_plan.validity_days),
            remain_request=selected_plan.api_calls,
            total_request=selected_plan.api_calls
        )
        db.add(new_user_plan)
        db.commit()

    # Create a payment record for the selected plan
    new_payment = Payment(
        user_id=user.id,
        amount=selected_plan.price,
        payment_type="subscription",
        payment_date=datetime.utcnow(),
        status="completed"  # Assuming payment was successful
    )
    db.add(new_payment)
    db.commit()

   

    return {"message": f"Plan changed to {selected_plan.name} successfully"}


@router.get("/current-user-plan")
def get_current_user_plan(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_plan = db.query(UserPlan).filter(UserPlan.user_id == current_user.id).first()
    if not user_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User plan not found")
    return user_plan




# @router.post("/change-user-plan/{plan_name}")
# def change_plan(plan_name: str, invoice_number: str, payment_method: str, payment_type: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
#     print("in Change user Token details:  ",current_user)
#     #  Check if the user exists
#     user = db.query(User).filter(User.id == current_user.id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     # Get the selected plan details
#     selected_plan = db.query(Plan).filter(Plan.name == plan_name).first()
#     if not selected_plan:
#         raise HTTPException(status_code=400, detail="Invalid plan selected")

#     # Get the user's current plan
#     current_user_plan = db.query(UserPlan).filter(UserPlan.user_id == current_user.id).first()

#     if current_user_plan:
#         # Update the user's current plan without modifying the id
#         current_user_plan.plan_name = selected_plan.name
#         current_user_plan.plan_buy_start_date = datetime.now()
#         current_user_plan.plan_expire_date = datetime.now() + timedelta(days=selected_plan.validity_days)
#         current_user_plan.remain_request += selected_plan.api_calls
#         current_user_plan.total_request += selected_plan.api_calls
#         db.commit()
#     else:
#         # Create a new user plan
#         new_user_plan = UserPlan(
#             user_id=current_user.id,
#             plan_name=selected_plan.name,
#             plan_buy_start_date=datetime.now(),
#             plan_expire_date=datetime.now() + timedelta(days=selected_plan.validity_days),
#             remain_request=selected_plan.api_calls,
#             total_request=selected_plan.api_calls
#         )
#         db.add(new_user_plan)
#         db.commit()

#     # Create a payment record for the selected plan
#     new_payment = Payment(
#         user_id=user.id,
#         amount=selected_plan.price,
#         payment_method=payment_method,
#         invoice_number=invoice_number,
#         payment_type=payment_type,
#         payment_date=datetime.utcnow(),
#         status="completed"  # Assuming payment was successful
#     )
#     db.add(new_payment)
#     db.commit()

#     return {"message": f"Plan changed to {selected_plan.name} successfully"}
