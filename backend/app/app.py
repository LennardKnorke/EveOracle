# backend/app/app.py
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.core.config import settings

from app.routers import auth
from app.routers.scheduled_tasks import scheduler



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting EveOracle API")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Background Tasks
    scheduler.start()

    yield  # The application runs while this yield is active
    
    scheduler.shutdown()

    print("Shutting down.")
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
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
async def root() -> dict:
    return {
        "message": "Welcome to Eve Oracle API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "timestamp": datetime.now().isoformat()
    }



app.include_router(auth.router)
#app.include_router(user.router)
#app.include_router(esi_zkill.router)
