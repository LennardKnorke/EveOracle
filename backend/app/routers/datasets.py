# backend/app/routers/datasets.py

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import UserAccount, get_db

router = APIRouter()


@router.get("dataset/datasets_sum")
async def get_dataset_summaries(authorization : str = Header(...), db : AsyncSession = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    session_key = authorization.replace("Bearer ", "")

    stmt = select(UserAccount).where(UserAccount.session_key == session_key)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        return {}