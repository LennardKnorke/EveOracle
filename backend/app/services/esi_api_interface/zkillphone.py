# backend/app/services/esi_api_interface/zkillphone.py

from datetime import date, timedelta
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
    
    def fetch_statistics(self, entity_type : str, entity_id : str):
        assert entity_type in self.entity_types, "Invalid entity type!"

        url = f"{ZKILL_API_URL}/stats/{entity_type}/{entity_id}/"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
    
        return response.json()
    
    def fetch_historic_data(self, dt: date):
        filename = f"{dt.year}{dt.month:02d}{dt.day:02d}.json"
        url = f"{ZKILL_HISTORY_URL}/{filename}"
        year_dir = Path("static/zkill") / str(dt.year)
        year_dir.mkdir(parents=True, exist_ok=True)
        filepath = year_dir / filename

        if filepath.exists():
            return
        try:
            req = requests.get(url=url, headers=self.headers)
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
        

ZPhone = ZkillPhone()