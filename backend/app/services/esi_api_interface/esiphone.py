# backend/app/services/esi_api_interface/esiphone.py

import requests
import string

from fastapi import HTTPException

from app.core.config import ESI_API_URL


class ESI_Phone:
    headers = {
        "application/json"
    }

    def fetch_esi_search(self, char_id : string, access_token : string, category : string, search : string, strict : bool = True):
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


    def fetch_esi_charids(self, characters : list[str]):
        url = f"{ESI_API_URL}/universe/ids/"
        headers = {
            "Accept": "application/json",
        }

        response = requests.post(url, headers=headers, json=characters)
        response.raise_for_status()

        return response.json()


    def fetch_character_standings(self, character_id : str, acess_token : str):
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


    def fetch_cooperation_standings(self, cooperation_id : str, acess_token : str):
        url = f"{ESI_API_URL}/characters/{cooperation_id}/standings"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {acess_token}"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()


    def fetch_alliance_publicinfo(self, alliance_id : str|int):
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


    def fetch_chars_affiliation(self, characters : list[str]):
        """
        Character affiliation
        https://esi.evetech.net//characters/affiliation
        """
        url = f"{ESI_API_URL}/characters/affiliation"

        headers = {
            "Accept": "application/json",
        }
        response = requests.post(url, headers=headers, json=characters)
        
        print(response.status_code)

        if response.status_code == 404:
            error_msg = response.json().get('error', 'Unknown error')
            if "not in a fleet" in error_msg.lower():
                return {}
            else:
                raise HTTPException(response.status_code, error_msg)
        elif response.status_code >=300:
            raise HTTPException(response.status_code)
        else:
            return response.json()


    def fetch_fitting(self, char_id : str|int, access_token : str):
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


    def fetch_char_fleetinfo(self, char_id : int|str, access_token : str) -> dict:
        """
        Get character fleet info
        https://esi.evetech.net/characters/{character_id}/fleet/
        """
        url = f"{ESI_API_URL}/characters/{char_id}/fleet"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(url, headers=headers)
        print(response.status_code)
        
        if response.status_code == 404:
            error_msg = response.json().get('error', 'Unknown error')
            if "not in a fleet" in error_msg.lower():
                return {}
            else:
                raise HTTPException(response.status_code, error_msg)
        elif response.status_code >=300:
            raise HTTPException(response.status_code)
        else:
            return response.json()

    def fetch_fleetinfo(self, fleet_id :int|str, access_token : str):
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

    def fetch_fleetmember(self, fleet_id :int|str, access_token : str):
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

        if response.status_code == 404:
            error_msg = response.json().get('error', 'Unknown error')
            if error_msg == "The fleet does not exist or you don't have access to it!":
                return []
            else:
                raise HTTPException(response.status_code, error_msg)
        elif response.status_code >=300:
            raise HTTPException(response.status_code)
        else:
            return response.json()


ESIPhone = ESI_Phone()