# backend/app/services/esi_api_interface/__init__.py

import base64
import random
import requests
import string
import urllib

from app.core.config import settings, ESI_TOKEN_URL, ESI_AUTH_URL, SCOPES, ESI_VERIFY_URL
from app.services.esi_api_interface import ESIPhone, ESI_Phone, ZkillPhone


def refresh_token(refresh_token : string):
    basic_auth = base64.urlsafe_b64encode(
        f"{settings.ESI_CLIENT_ID}:{settings.ESI_CLIENT_SECRET}".encode("utf-8")
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
        f"{settings.ESI_CLIENT_ID}:{settings.ESI_CLIENT_SECRET}".encode("utf-8")
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
        "client_id": settings.ESI_CLIENT_ID,
        "redirect_uri": settings.ESI_CALLBACK_URL,
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




__all__ = [
    "ZkillPhone",
    "ESIPhone", "ESI_Phone",
    "verify_account", "redirect_to_sso", "request_token", "refresh_token"
]