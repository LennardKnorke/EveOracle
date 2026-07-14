"""
Builds ships.json from Eve Online SDE JSONL files.
Output: { "typeID": { name, shipClass, faction, mass, volume, attributes: { attrName: value } } }
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "eve-online-static-data-3393779-jsonl")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "ships.json")


def load_jsonl(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def main():
    print("Loading factions...")
    faction_map = {}  # factionID -> name
    for row in load_jsonl("factions.jsonl"):
        faction_map[row["_key"]] = row["name"]["en"]

    print("Loading ship groups...")
    group_map = {}  # groupID -> name (only category 6 = Ship)
    for row in load_jsonl("groups.jsonl"):
        if row.get("categoryID") == 6:
            group_map[row["_key"]] = row["name"]["en"]

    print("Loading dogma attribute names...")
    attr_name_map = {}  # attributeID -> name
    for row in load_jsonl("dogmaAttributes.jsonl"):
        if row.get("name"):
            attr_name_map[row["_key"]] = row["name"]

    print("Loading ship types...")
    ship_base = {}  # typeID -> base info
    for row in load_jsonl("types.jsonl"):
        if row.get("groupID") in group_map and row.get("published"):
            ship_base[row["_key"]] = {
                "name": row["name"]["en"],
                "shipClass": group_map[row["groupID"]],
                "faction": faction_map.get(row.get("factionID")),
                "mass": row.get("mass"),
                "volume": row.get("volume"),
            }

    print(f"  Found {len(ship_base)} published ships")

    print("Loading dogma attributes per ship...")
    ship_dogma = {}  # typeID -> {attrName: value}
    for row in load_jsonl("typeDogma.jsonl"):
        type_id = row["_key"]
        if type_id not in ship_base:
            continue
        attrs = {}
        for entry in row.get("dogmaAttributes", []):
            attr_id = entry["attributeID"]
            name = attr_name_map.get(attr_id)#, f"attr_{attr_id}")
            attrs[name] = entry["value"]
        ship_dogma[type_id] = attrs

    print("Assembling output...")
    ships = {}
    for type_id, base in ship_base.items():
        ships[str(type_id)] = {
            "name": base["name"],
            "shipClass": base["shipClass"],
            "faction": base["faction"],
            "mass": base["mass"],
            "volume": base["volume"],
            "attributes": ship_dogma.get(type_id, {}),
        }

    print(f"Writing {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(ships, f, indent=2, ensure_ascii=False)

    print(f"Done. {len(ships)} ships written to ships.json")


if __name__ == "__main__":
    main()
