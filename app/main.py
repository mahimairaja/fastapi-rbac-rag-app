import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import init_db
from app.routers import auth, users, rag
from app.auth.authorization import init_oso
from dotenv import load_dotenv
from datetime import datetime

logging.basicConfig(filename='app.log', level=logging.INFO)
logging.info(f"Starting the application at {datetime.now()}")
logger = logging.getLogger(__name__)

load_dotenv()

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
allowed_origins = ALLOWED_ORIGINS.split(",")

app = FastAPI(
    title="FastAPI RAG RBAC Service",
    description="A RESTful API service with JWT authentication, RBAC, and RAG capabilities",
    version="0.0.1"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True, 
    allow_methods=["*"], # TODO: Restrict this to only the necessary methods
    allow_headers=["*"], # TODO: Restrict this to only the necessary headers
)


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(rag.router)


@app.on_event("startup")
async def startup_event():
    init_db()
    init_oso()
    logger.info("Application started successfully.")


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the FastAPI RAG RBAC Service Demo"} 