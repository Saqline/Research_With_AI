from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import Plan # Import your models
import logging
from .database import Base, engine, get_db  # Import Base and engine from database
from .api.docs import router as docs_router
from .api.search.search import router as search_router
from .api.apikey import router as apikey_router
from .api.requestLog import router as requestLog_router
from .api.auth import router as main_router
from .api.model_rate_limit import router as model_rate_limit_router
from .api.plan import router as plan_router
from .api.payment.stripe import router as stripe_router
from sqlalchemy.orm import sessionmaker, Session, relationship

app = FastAPI(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://searchapi.sobjanta.ai",
        "https://shopnobash.com",
        "http://localhost:5173",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# Logging configuration
logging.basicConfig(level=logging.INFO)

# Create the database tables
# logging.info("Creating all tables...")
# Base.metadata.create_all(bind=engine)
# logging.info("Tables created!")
try:
    logging.info("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    logging.info("Tables created successfully!")
except Exception as e:
    logging.error(f"Error creating tables: {e}")

app.include_router(main_router)
app.include_router(docs_router)
app.include_router(search_router)
app.include_router(apikey_router)
app.include_router(requestLog_router)
app.include_router(model_rate_limit_router)
app.include_router(plan_router)
app.include_router(stripe_router)

initial_plans = [
    {"name": "Explorer", "api_calls": 1200, "price": 0, "validity_days": 30},
    {"name": "Project", "api_calls": 5000, "price": 20, "validity_days": 30},
    {"name": "Initiative", "api_calls": 20000, "price": 70, "validity_days": 30},
    {"name": "Startup", "api_calls": 30000, "price": 80, "validity_days": 30},
    {"name": "Enterprise", "api_calls": 100000, "price": 300, "validity_days": 30},
    {"name": "On-demand", "api_calls": 10000, "price": 50, "validity_days": 30}
]

@app.on_event("startup")
def create_initial_plans():
    db: Session = next(get_db()) 
    for plan in initial_plans:
        existing_plan = db.query(Plan).filter(Plan.name == plan["name"]).first()
        if not existing_plan:
            new_plan = Plan(
                name=plan["name"],
                api_calls=plan["api_calls"],
                price=plan["price"],
                validity_days=plan["validity_days"]
            )
            db.add(new_plan)
    db.commit()
