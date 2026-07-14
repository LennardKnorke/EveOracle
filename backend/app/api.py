# backend/app/api.py
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anyio


# Import our database helpers and models
from database import get_db, Base, engine
from database_models.useraccount import UserAccount

from config import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database init
    print("Starting up... Creating database tables if they do not exist.")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield  # The application runs while this yield is active
    
    print("Shutting down... Cleaning up database connections.")
    await engine.dispose()
    return


app = FastAPI(
    title="Eve Oracle API",
    description="API for Eve Oracle application",
    version="1.0.0",
    docs_url="/api/docs",
    lifespan=lifespan
)

origins = [
    "http://localhost:5173",
    "localhost:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount(
    "/static",
    StaticFiles(directory="esi_static_data"),
    name="static"
)


@app.get("/")
async def root() -> dict:
    return {
        "message": "Welcome to Eve Oracle API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "timestamp": datetime.now().isoformat()
    }

from app.routers import auth, user, esi_zkill

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(esi_zkill.router)
