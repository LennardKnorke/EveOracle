# /backend/app/routers/char.py
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Header, Cookie, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from shared.config import settings
from shared.esiphone import ESIPhone
from shared.zkillphone import ZkillPhone

from app.database import UserAccount, get_db
from app.routers.auth import get_valid_access_token



router = APIRouter()




@router.get("/char/currentFleet")
async def get_currentFleet(char_id : str, access_token : str = Depends(get_valid_access_token)):
    data : dict = ESIPhone.fetch_char_fleetinfo(char_id, access_token)
    ids = [char_id]

    chars = {}

    if len(data.items()) > 0:
        fleet_id = data['fleet_id']

        member_ids = ESIPhone.fetch_fleetmember(fleet_id, access_token)

        for id in member_ids:
            i = id['character_id']
            if i not in ids:
                ids.append(i)

    for i in ids:
        try:
            chars[i] = ZkillPhone.fetch_statistics('characterID', i)
        except:
            chars[i] = {}
    
    return chars

class CharStatsRequest(BaseModel):
    char_names: list[str | int]
@router.post("/char/stats")
def get_char_stats(body: CharStatsRequest, response: Response, session: str = Cookie(None, alias="session"), db : AsyncSession = Depends(get_db)):
    characters = body.char_names
    char_ids = ESIPhone.fetch_esi_charids(characters)
    chars = char_ids['characters']

    print(chars)
    results = {}
    for entry in chars:
        id = entry['id']
        try:
            
            results[id] = ZkillPhone.fetch_statistics('characterID', id)
        except:
            results[id] = {}
    return results