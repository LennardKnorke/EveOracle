# backend/esi_config.py

import os
from pathlib import Path

from pydantic_settings import BaseSettings


APPLICATION_NAME = "EveOracle"

class Settings(BaseSettings):
    ESI_CLIENT_ID : str
    ESI_CLIENT_SECRET : str

    FRONTEND_PORT : int = 3000
    FRONTEND_URL : str = "http://localhost"

    DATABASE_URL : str

    STATIC_PATH: str = "/app/data"

    BACKEND_PORT: int = 8000


    class Config:
        env_file = ".env"

settings = Settings()



### URLS
ESI_AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"
ESI_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
ESI_VERIFY_URL = "https://login.eveonline.com/oauth/verify"

ESI_API_URL = "https://esi.evetech.net"
ESI_IMG_URL = "https://images.evetech.net"

# ZKILLBOARD
ZKILL_API_URL = "https://zkillboard.com/api"



# SCOPES
SCOPES_FILE = Path("static/esi_rights.txt")
def load_scopes() -> list[str]:
    with open(SCOPES_FILE) as f:
        return [line.strip() for line in f if line.strip()]
SCOPES = load_scopes()
