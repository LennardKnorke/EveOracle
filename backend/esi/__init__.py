
from datetime import datetime
import json
import os
import requests

import base64
import random
import requests
import string
import urllib

from .zkillfetch import fetch_zkill_statistic
from .esifetch import fetch_esi_search, fetch_esi_charids

from config import *

def refresh_token(refresh_token : string):
    basic_auth = base64.urlsafe_b64encode(
        f"{ESI_CLIENT_ID}:{ESI_CLIENT_SECRET}".encode("utf-8")
    ).decode()

    payload = {
        "grant_type":"refresh_token",
        "refresh_token" : refresh_token
    }
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = requests.post(
        ESI_TOKEN_URL,
        headers=headers,
        data=payload
    )
    response.raise_for_status()
    new_tokens = response.json()
    data = verify_account(new_tokens)
    
    new_tokens["ExpiresOn"] = data["ExpiresOn"]
    return new_tokens


def request_token(authorization_code):
    basic_auth = base64.urlsafe_b64encode(
        f"{ESI_CLIENT_ID}:{ESI_CLIENT_SECRET}".encode("utf-8")
    ).decode()
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "authorization_code",
        "code": authorization_code,
    }
    response = requests.post(
        ESI_TOKEN_URL, headers=headers, data=payload
    )
    response.raise_for_status()

    return response.json()


def redirect_to_sso():    
    state = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    query_params = {
        "response_type": "code",
        "client_id": ESI_CLIENT_ID,
        "redirect_uri": ESI_CLIENT_CALLBACK_URL,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    query_string = urllib.parse.urlencode(query_params)
    return f"{ESI_AUTH_URL}?{query_string}", state


def verify_account(auth : dict):
    headers = {
        "Authorization": f"Bearer {auth["access_token"]}"
    }
    response = requests.get(
        ESI_VERIFY_URL,
        headers=headers
    )
    response.raise_for_status()
    return response.json()