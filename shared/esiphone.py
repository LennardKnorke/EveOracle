# shared/esiphone.py

import requests
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from shared.config import ESI_API_URL


class ESI_Phone:
    default_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    def fetch_esi_search(self, char_id: str | int, access_token: str, category: str, search: str, strict: bool = True):
        url = f"{ESI_API_URL}/latest/search/"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        params = {
            "categories": category,
            "search": search,
            "strict": "true" if strict else "false"
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_esi_charids(self, characters: List[str]) -> Dict[str, Any]:
        """Resolves names to character IDs via /latest/universe/ids/"""
        url = f"{ESI_API_URL}/latest/universe/ids/"
        response = requests.post(url, headers=self.default_headers, json=characters)
        response.raise_for_status()
        return response.json()

    def fetch_esi_names(self, ids: List[int]) -> List[Dict[str, Any]]:
        """Resolves IDs to names via /latest/universe/names/"""
        if not ids:
            return []
        url = f"{ESI_API_URL}/latest/universe/names/"
        response = requests.post(url, headers=self.default_headers, json=ids)
        response.raise_for_status()
        return response.json()

    def fetch_chars_affiliation(self, characters: List[int]) -> List[Dict[str, Any]]:
        """Fetches corp and alliance affiliation for a list of character IDs"""
        if not characters:
            return []
        url = f"{ESI_API_URL}/latest/characters/affiliation/"
        response = requests.post(url, headers=self.default_headers, json=characters)
        response.raise_for_status()
        return response.json()

    def fetch_character_contacts(self, character_id: str | int, access_token: str) -> List[Dict[str, Any]]:
        """
        Get character contacts and standings.
        https://esi.evetech.net/latest/characters/{character_id}/contacts/
        """
        url = f"{ESI_API_URL}/latest/characters/{character_id}/contacts/"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json()

    def fetch_char_fleetinfo(self, char_id: int | str, access_token: str) -> Dict[str, Any]:
        """Get character fleet info. Returns {} if not in fleet."""
        url = f"{ESI_API_URL}/latest/characters/{char_id}/fleet/"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json()

    def fetch_fleetmember(self, fleet_id: int | str, access_token: str) -> List[Dict[str, Any]]:
        """Get list of fleet members."""
        url = f"{ESI_API_URL}/latest/fleets/{fleet_id}/members/"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code in (403, 404):
            return []
        response.raise_for_status()
        return response.json()


ESIPhone = ESI_Phone()