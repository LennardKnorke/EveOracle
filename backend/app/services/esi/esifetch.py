

import requests

import requests
import string

from backend.app.core.config import ESI_API_URL

def fetch_esi_search(char_id : string, access_token : string, category : string, search : string, strict : bool = True):
    url = f"{ESI_API_URL}/latest/search/"
    headers = {
        "Accept": "application/json",
        "Authorization" : f"Bearer {access_token}"
    }
    params = {
        "categories": category,
        "search": search,
        "strict": "true" if strict else "false"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()


def fetch_esi_charids(characters : list[str]):
    url = f"{ESI_API_URL}/universe/ids/"
    headers = {
        "Accept": "application/json",
    }

    response = requests.post(url, headers=headers, json=characters)
    response.raise_for_status()

    return response.json()


def fetch_character_standings(character_id : str, acess_token : str):
    """
    Get standings
    https://esi.evetech.net/characters/{character_id}/standings
    """
    url = f"{ESI_API_URL}/characters/{character_id}/standings"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {acess_token}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def fetch_cooperation_standings(cooperation_id : str, acess_token : str):
    url = f"{ESI_API_URL}/characters/{cooperation_id}/standings"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {acess_token}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def fetch_alliance_publicinfo(alliance_id : str|int):
    """
    Get alliance's public information
    https://esi.evetech.net/alliances/{alliance_id}
    """

    url = f"{ESI_API_URL}/alliances/{alliance_id}"

    headers = {
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def fetch_chars_affiliation(characters : list[str]):
    """
    Character affiliation
    https://esi.evetech.net//characters/affiliation
    """
    url = f"{ESI_API_URL}/characters/affiliation"

    headers = {
        "Accept": "application/json",
    }
    response = requests.post(url, headers=headers, json=characters)
    response.raise_for_status()

    return response.json()


def fetch_fitting(char_id : str|int, access_token : str):
    """
    Get fittings
    https://esi.evetech.net/characters/{character_id}/fittings
    """
    url = f"{ESI_API_URL}/characters/{char_id}/fittings"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def fetch_char_fleetinfo(char_id : int|str, access_token : str):
    """
    Get character fleet info
    https://esi.evetech.net/characters/{character_id}/fleet
    """
    url = f"{ESI_API_URL}/characters/{char_id}/fleet"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()

def fetch_fleetinfo(fleet_id :int|str, access_token : str):
    """
    Get fleet information
    https://esi.evetech.net/fleets/{fleet_id}
    """
    url = f"{ESI_API_URL}/fleets/{fleet_id}"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()

def fetch_fleetmember(fleet_id :int|str, access_token : str):
    """
    Get fleet members
    https://esi.evetech.net/fleets/{fleet_id}/members
    """
    url = f"{ESI_API_URL}/fleets/{fleet_id}/members"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()