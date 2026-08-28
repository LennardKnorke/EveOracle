# backend/app/routers/char.py

import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from shared.config import STATIC_DIR
from shared.esiphone import ESIPhone
from shared.zkillphone import ZkillPhone
from app.database import get_db
from app.routers.auth import get_valid_access_token, get_current_user

logger = logging.getLogger("uvicorn.error")  

router = APIRouter()



class CharStatsRequest(BaseModel):
    char_names: List[str]
    existing_char_ids: Optional[List[int | str]] = []


def calculate_standing(
    char_id: int,
    corp_id: Optional[int],
    alliance_id: Optional[int],
    user_char_id: int,
    user_corp_id: Optional[int],
    user_alliance_id: Optional[int],
    contacts_map: Dict[int, float]
) -> Optional[float]:
    """
    Computes standing:
    - User itself -> None
    - Explicit contact (character, corp, or alliance) -> contact standing
    - Same alliance/corp -> +10.0
    - Otherwise -> 0.0 (Neutral)
    """
    if char_id == user_char_id:
        return 10.0

    # Check direct contact by character ID
    if char_id in contacts_map:
        return contacts_map[char_id]

    # Check corp contact
    if corp_id and corp_id in contacts_map:
        return contacts_map[corp_id]

    # Check alliance contact
    if alliance_id and alliance_id in contacts_map:
        return contacts_map[alliance_id]

    # Check shared alliance or corp
    if user_alliance_id and alliance_id and user_alliance_id == alliance_id:
        return 10.0
    if user_corp_id and corp_id and user_corp_id == corp_id:
        return 10.0

    return 0.0


def build_contacts_map(contacts_raw: List[Dict[str, Any]]) -> Dict[int, float]:
    return {c["contact_id"]: float(c.get("standing", 0.0)) for c in contacts_raw}


def open_ships():
    with open(STATIC_DIR / 'esi_static_data' / 'ships.json', 'r') as file:
        data= json.load(file)
    return data

@router.get("/char/currentFleet")
async def get_current_fleet(
    char_id: int = Query(..., description="Character ID of the user"),
    access_token: str = Depends(get_valid_access_token)
):
    """
    Fetches stats, affiliation, and standings for all fleet members.
    """
    # 1. Get user affiliation & contacts to determine standings
    user_affiliations = ESIPhone.fetch_chars_affiliation([char_id])
    user_corp_id = user_affiliations[0].get("corporation_id") if user_affiliations else None
    user_alliance_id = user_affiliations[0].get("alliance_id") if user_affiliations else None

    contacts_raw = ESIPhone.fetch_character_contacts(char_id, access_token)
    contacts_map = build_contacts_map(contacts_raw)

    # 2. Check fleet
    fleet_info = ESIPhone.fetch_char_fleetinfo(char_id, access_token)
    logger.warning(fleet_info)

    if not fleet_info or "fleet_id" not in fleet_info:
        return []

    fleet_id = fleet_info["fleet_id"]
    

    members_raw = ESIPhone.fetch_fleetmember(fleet_id, access_token)
    if not members_raw:
        return []
    
    ship_data = open_ships()
    member_char_ids = [m["character_id"] for m in members_raw]
    member_ship_map = {m["character_id"]: m.get("ship_type_id") for m in members_raw}


    # 3. Resolve names & affiliations
    names_data = ESIPhone.fetch_esi_names(member_char_ids)
    names_map = {n["id"]: n["name"] for n in names_data}

    affiliations_data = ESIPhone.fetch_chars_affiliation(member_char_ids)
    affil_map = {a["character_id"]: a for a in affiliations_data}

    # 4. Fetch zKill stats & build response
    results = []
    for cid in member_char_ids:
        affil = affil_map.get(cid, {})
        corp_id = affil.get("corporation_id")
        alli_id = affil.get("alliance_id")
        name = names_map.get(cid, f"Pilot {cid}")

        try:
            stats = ZkillPhone.fetch_statistics("characterID", cid) or {}
        except Exception:
            stats = {}

        standing = calculate_standing(
            char_id=cid,
            corp_id=corp_id,
            alliance_id=alli_id,
            user_char_id=char_id,
            user_corp_id=user_corp_id,
            user_alliance_id=user_alliance_id,
            contacts_map=contacts_map
        )

        ship_id = member_ship_map.get(cid)
        ship_info = ship_data.get(str(ship_id), {}) if ship_id else {}
        ship_name = ship_info.get("name")
        ship_class = ship_info.get("shipClass")
        
        results.append({
            "char_id": cid,
            "char_name": name,
            "corporation_id": corp_id,
            "alliance_id": alli_id,
            "standing": standing,
            "ship_id": ship_id,
            "ship_name": ship_name,
            "ship_class": ship_class,
            "stats": stats
        })

    return results


@router.post("/char/stats")
async def get_char_stats(
    body: CharStatsRequest,
    access_token: str = Depends(get_valid_access_token),
    current_user = Depends(get_current_user)
):
    """
    Resolves names from pasted local chat, filters already cached pilots,
    and returns stats + standings.
    """
    
    if not body.char_names:
        return []

    # 1. Resolve character names to IDs
    esi_id_lookup = ESIPhone.fetch_esi_charids(body.char_names)
    matched_chars = esi_id_lookup.get("characters", [])
    if not matched_chars:
        return []

    # Filter out already existing characters
    existing_ids_set = {int(x) for x in (body.existing_char_ids or []) if str(x).isdigit()}
    chars_to_fetch = [c for c in matched_chars if c["id"] not in existing_ids_set]
    if not chars_to_fetch:
        return []

    char_ids = [c["id"] for c in chars_to_fetch]
    names_map = {c["id"]: c["name"] for c in chars_to_fetch}

    # 2. Safely get user_id from dict or model
    if isinstance(current_user, dict):
        raw_user_id = current_user.get("id") or current_user.get("char_id") or current_user.get("character_id")
    else:
        raw_user_id = getattr(current_user, "id", None) or getattr(current_user, "char_id", None)

    if not raw_user_id:
        raise HTTPException(status_code=401, detail="Could not determine authenticated user ID")

    user_id = int(raw_user_id)

    user_affiliations = ESIPhone.fetch_chars_affiliation([user_id])
    user_corp_id = user_affiliations[0].get("corporation_id") if user_affiliations else None
    user_alliance_id = user_affiliations[0].get("alliance_id") if user_affiliations else None

    contacts_raw = ESIPhone.fetch_character_contacts(user_id, access_token)
    contacts_map = build_contacts_map(contacts_raw)
    

    # 3. Fetch affiliations for target characters
    affiliations_data = ESIPhone.fetch_chars_affiliation(char_ids)
    affil_map = {a["character_id"]: a for a in affiliations_data}

    # 4. Fetch zKillboard stats and assemble result
    results = []
    for cid in char_ids:
        affil = affil_map.get(cid, {})
        corp_id = affil.get("corporation_id")
        alli_id = affil.get("alliance_id")
        name = names_map.get(cid, f"Pilot {cid}")

        try:
            stats = ZkillPhone.fetch_statistics("characterID", cid) or {}
        except Exception:
            stats = {}

        standing = calculate_standing(
            char_id=cid,
            corp_id=corp_id,
            alliance_id=alli_id,
            user_char_id=user_id,
            user_corp_id=user_corp_id,
            user_alliance_id=user_alliance_id,
            contacts_map=contacts_map
        )

        results.append({
            "char_name": name,
            "char_id": cid,
            "corporation_id": corp_id,
            "alliance_id": alli_id,
            "standing": standing,
            "ship_type_id" : None,
            "shipName" : None,
            "shipClass" : None,
            "stats": stats
        })

    return results