# backend/app/app.py
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from shared.config import settings, STATIC_DIR

from app.routers import auth, char, ship, model
#from app.routers.scheduled_tasks import scheduler



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting EveOracle API")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
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

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    print(f"[WARN] Static directory not found at: {STATIC_DIR}")


@app.get("/")
async def root() -> dict:
    return {
        "message": "Welcome to Eve Oracle API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "timestamp": datetime.now().isoformat()
    }



app.include_router(auth.router)
app.include_router(char.router)
app.include_router(ship.router)
app.include_router(model.router)