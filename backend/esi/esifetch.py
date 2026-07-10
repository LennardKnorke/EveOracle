

from datetime import datetime
import json
import os
import requests

import base64
import random
import requests
import string
import urllib

from config import ESI_CLIENT_ID, ESI_API_URL, ESI_IMG_URL

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


def fetch_esi_img(category : string, id : str, variation : str|None = None):
    image_categories = [
        "alliances"
        "characters"
        "corporations"
        "types"
    ]
    if category not in image_categories:
        raise ValueError("Invalid Category")
    
    url = f"{ESI_IMG_URL}/{category}/{id}"
    if variation:
        url += f"/{variation}"

    headers = {

    }
    response = requests.get(
        url,
    )

    response.raise_for_status()
    return response