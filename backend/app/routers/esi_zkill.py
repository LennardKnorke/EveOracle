#backend/app/routers/zfetch.py

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import UserAccount, get_db
from services.esi import fetch_zkill_statistic, fetch_esi_charids, fetch_cooperation_standings


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
    
    characters = request.characters

    id_results = fetch_esi_charids(characters)
    id_results = id_results['characters']
    results = {}
    for char in id_results:
        id = char['id']
        name = str(char['name'])

        char_results = fetch_zkill_statistic('characterID', id)
        results[name] = {
            "char_id" : id,
            "name" : name,
            "corporationID" : char_results['info']['corporationID'],
            "allianceID" : char_results['info']['allianceID'],
            "stats" : char_results
        }
    return results



@router.post("/standings/cooperation")
async def get_cooperation_standings(cooperation_id : str, authorization : str = Header(...), db : AsyncSession = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    session_key = authorization.replace("Bearer ", "")
    stmt = select(UserAccount).where(UserAccount.session_key == session_key)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        return {}

    access_token = existing_user.access_token

    data = fetch_cooperation_standings(cooperation_id, access_token)
    return data


