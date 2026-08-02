import requests

import requests



from app.core.config import ZKILL_API_URL

STATS_ENTITIES = [
    "characterID",
    "corporationID",
    "allianceID",
    "factionID",
    "shipTypeID",
    "groupID",
    "solarSystemID",
    "regionID"
]

def fetch_zkill_statistic(entity_type : str, entity_id : str):
    if entity_type not in STATS_ENTITIES:
        raise ValueError("Invalid entity type!")
    
    headers = {
        "Accept-Encoding": "gzip",
        "User-Agent": "EveOracle"
    }
    
    url = f"{ZKILL_API_URL}/stats/{entity_type}/{entity_id}/"
    response = requests.get(url, headers=headers)

    response.raise_for_status()
    
    return response.json()