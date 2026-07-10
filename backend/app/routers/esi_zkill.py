#backend/app/routers/zfetch.py

from datetime import datetime
import hashlib
import secrets
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database_models.useraccount import UserAccount
from database import get_db
from esi import fetch_zkill_statistic, fetch_esi_search, fetch_esi_charids


router = APIRouter()

class CharStatsRequest(BaseModel):
    characters: list[str]

@router.post("/stats/char/")
async def get_char_stats(request : CharStatsRequest, authorization : str = Header(...), db : AsyncSession = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    session_key = authorization.replace("Bearer ", "")
    stmt = select(UserAccount).where(UserAccount.session_key == session_key)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        return {}
    
    char_id = existing_user.char_id
    access_token = existing_user.access_token
    characters = request.characters

    id_results = fetch_esi_charids(characters)['characters']
    results = []
    for char in id_results:
        id = char['id']
        name = char['name']

        char_results = fetch_zkill_statistic('characterID', id)
        char_results['id'] = id
        char_results['name'] = name
        results.append(char_results)

    return {
        "results" : results
    }
