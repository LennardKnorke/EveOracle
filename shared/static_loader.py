

import json

from shared.config import STATIC_DIR, SHIP_FILE


EVE_STATIC_DATA_DIR = STATIC_DIR / "eve-online-static-data"


def load_categories()-> None|dict:
    path = EVE_STATIC_DATA_DIR / "categories.jsonl"
    if not path.exists():
        return None

    allowed_categories = {
        "Material", "Accessories", "Ship", "Module", "Charge", "Drone", "Fighter",
        "Trading", "Skill", "Implant", "Deployable", "Reaction",
        "Subsystem", "Decryptors", "Infrastructure Upgrades", "Planetary Industry",
        "Planetary Resources", "Planetary Commodities", "Placeables",
        "Structure Module", "Colony Resources",
    }

    allowed_cat = {}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            name = obj.get("name", {}).get("en")
            if name in allowed_categories:
                obj["name"] = name
                allowed_cat[obj["_key"]] = obj
    
    return allowed_cat if allowed_cat else None


def load_groups(allowed_categories: dict):
    path = EVE_STATIC_DATA_DIR / "groups.jsonl"

    if not path.exists() or not allowed_categories:
        return None

    allowed_grps = {}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("categoryID") in allowed_categories:
                obj["name"] = obj.get("name", {}).get("en")
                allowed_grps[obj["_key"]] = obj
    return allowed_grps if allowed_grps else None


def load_types() -> list[str]:
    cats = load_categories()
    if not cats:
        return []
    grp = load_groups(cats)
    if not grp:
        return []

    path = EVE_STATIC_DATA_DIR / "types.jsonl"
    if not path.exists():
        return []

    data = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("groupID") not in grp:
                continue
            if obj.get("basePrice", False) == False:
                continue

            data.append(str(obj["_key"]))

    return data



def load_ship_ids()->list[str]:
    with open(SHIP_FILE, "r", encoding="utf-8") as f:
        ships_data = json.load(f)
    return ships_data