# backend/esi_config.py

import os
import json

from dotenv import load_dotenv
load_dotenv()

APPLICATION_NAME = "EveOracle"


# BATTLE_SIZES
BATTLE_SIZES = [5, 10, 20]  # Maximum number of ships per party


### ENVIRONMENT VARIABLES
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8080")
BACKEND_URL = os.environ.get("BACKEND_PORT", "localhost")

FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "5173")
FRONTEND_URL = os.environ.get("BACKEND_PORT", "localhost")


# EVE ONLINE
ESI_CLIENT_ID = os.environ.get("ESI_CLIENT_ID", None)
ESI_CLIENT_SECRET = os.environ.get("ESI_CLIENT_SECRET", None)




# DATABASE
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_USER = os.environ.get("DB_USER")
DB_DBNAME = os.environ.get("DB_DBNAME")

### URLS
# EVE ONLINE
ESI_CLIENT_CALLBACK_URL = f"http://{BACKEND_URL}:{BACKEND_PORT}/auth/callback"

ESI_AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"
ESI_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
ESI_VERIFY_URL = "https://login.eveonline.com/oauth/verify"

ESI_API_URL = "https://esi.evetech.net"
ESI_IMG_URL = "https://images.evetech.net"

# ZKILLBOARD
ZKILL_API_URL = "https://zkillboard.com/api"


# SCOPES
SCOPES_FILE = os.path.join(os.path.dirname(__file__), "esi_rights.txt")
def load_scopes() -> list[str]:
    with open(SCOPES_FILE) as f:
        return [line.strip() for line in f if line.strip()]
SCOPES = load_scopes()