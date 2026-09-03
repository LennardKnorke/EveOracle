# shared/zkillphone.py

from datetime import date
import json
from pathlib import Path
import requests
from urllib.error import HTTPError


ZKILL_API_URL = "https://zkillboard.com/api"
ZKILL_HISTORY_URL = "https://r2z2.zkillboard.com/history/raw"

class ZkillPhone:
    headers = {
        "Accept-Encoding": "gzip",
        "User-Agent": "EveOracle",
        "content-type" : "application/json"
    }

    entity_types = [
        "characterID",
        "corporationID",
        "allianceID",
        "factionID",
        "shipTypeID",
        "groupID",
        "solarSystemID",
        "regionID"
    ]
    
    @staticmethod
    def fetch_statistics(entity_type : str, entity_id : str):
        assert entity_type in ZkillPhone.entity_types, "Invalid entity type!"

        url = f"{ZKILL_API_URL}/stats/{entity_type}/{entity_id}/"

        response = requests.get(url, headers=ZkillPhone.headers)
        response.raise_for_status()
    
        return response.json()
    
    @staticmethod
    def fetch_historic_data(dt: date):
        filename = f"{dt.year}{dt.month:02d}{dt.day:02d}.json"
        url = f"{ZKILL_HISTORY_URL}/{filename}"
        year_dir = Path("static/zkill") / str(dt.year)
        year_dir.mkdir(parents=True, exist_ok=True)
        filepath = year_dir / filename

        if filepath.exists():
            return
        try:
            req = requests.get(url=url, headers=ZkillPhone.headers)
            data = req.json()
            with open(filepath, 'w') as f:
                json.dump(data, fp=f,indent=4)
                print(f"Fetched Killmails from {dt}")        
        except HTTPError as e:
            if e.code == 404:
                print(f"Missing: {filename}")
            else:
                print(f"HTTP {e.code}: {filename}")
        except Exception as e:
            print(f"Failed {filename}: {e}")
        return
    
    @staticmethod
    def fetch_price_history(type_id : str):
        type_str = str(type_id)
        assert type_str.isdigit(), "Type Needs to be an Integer"
        url = f"https://zkillboard.com/api/prices/{type_str}/"
        response = requests.get(
            url,
            timeout=30,
            headers=ZkillPhone.headers
        )
        response.raise_for_status()
        return response.json()