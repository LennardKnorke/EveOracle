# shared/config.py

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

APPLICATION_NAME = "EveOracle"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if Path("/static").exists():
    STATIC_DIR = Path("/static")
else:
    STATIC_DIR = PROJECT_ROOT / "static"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


    ESI_CLIENT_ID: str = ""
    ESI_CLIENT_SECRET: str = ""
    ESI_CALLBACK_URL: str = ""

    FRONTEND_PORT: int = 5173
    FRONTEND_URL: str = "localhost"

    DB_USER: str = "eveuser"
    DB_PASSWORD: str = ""
    DB_DBNAME: str = "eveoracle"
    DB_ADDRESS: str = "localhost"
    DB_PORT: int = 3306
    DATABASE_URL: Optional[str] = None

    BACKEND_PORT: int = 8080
    ENV: str = "development"

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_ADDRESS}:{self.DB_PORT}/{self.DB_DBNAME}"


settings = Settings()


### URLS
ESI_AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"
ESI_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
ESI_VERIFY_URL = "https://login.eveonline.com/oauth/verify"

ESI_API_URL = "https://esi.evetech.net"
ESI_IMG_URL = "https://images.evetech.net"



# SCOPES
def load_scopes() -> list[str]:
    with open(STATIC_DIR / "esi_rights.txt") as f:
        return [line.strip() for line in f if line.strip()]
SCOPES = load_scopes()


KILLMAILS_DIR = STATIC_DIR / "killmail_history" / "zkill"
PRICES_DIR = STATIC_DIR / "Prices" if (STATIC_DIR / "Prices").exists() else STATIC_DIR / "prices"
SHIP_FILE = STATIC_DIR / "esi_static_data" / "ships.json"
SHIP_STATS_DIR = STATIC_DIR / "esi_static_data" / "ship_stats"
SNAPSHOTS_DIR = STATIC_DIR / "snapshots" / "monthly"
MODELS_DIR = STATIC_DIR / "output" / "models"