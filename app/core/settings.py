import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Base
    APP_NAME: str = "Fiogora"
    VERSION: str = "1.0.0"

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DOWNLOADS_DIR: Path = BASE_DIR / "downloads"
    CORE_DIR_PATH: Path = Path(__file__).resolve().parent
    CONSTANTS_JSON_PATH: Path = CORE_DIR_PATH / "constants.json"

    # Browser / Automation
    HEADLESS_MODE: bool = os.getenv("HEADLESS_MODE", "True").lower() == "true"
    FIORILLI_URL: str = os.getenv("FIORILLI_URL", "")
    AHGORA_URL: str = os.getenv("AHGORA_URL", "")
    LEAVES_MONTHS_AGO: int = int(os.getenv("LEAVES_MONTHS_AGO", "2"))

    # Credentials
    FIORILLI_USER: str = os.getenv("FIORILLI_USER", "")
    FIORILLI_PASSWORD: str = os.getenv("FIORILLI_PASSWORD", "")
    AHGORA_USER: str = os.getenv("AHGORA_USER", "")
    AHGORA_PASSWORD: str = os.getenv("AHGORA_PASSWORD", "")
    AHGORA_COMPANY: str = os.getenv("AHGORA_COMPANY", "")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/fiogora"
    )

    def __init__(self):
        self._constants = self._load_constants()
        
        self.UPLOAD_LEAVES_COLUMNS = self._constants.get("upload_leaves_columns", [])
        self.LEAVES_COLUMNS = self._constants.get("leaves_columns", [])
        self.AHGORA_EMPLOYEES_COLUMNS = self._constants.get("ahgora_employees_columns", [])
        self.FIORILLI_EMPLOYEES_COLUMNS = self._constants.get("fiorilli_employees_columns", [])
        self.COLUMNS_TO_VERIFY_CHANGE = self._constants.get("columns_to_verify_change", [])
        self.PT_MONTHS = self._constants.get("pt_months", {})
        self.EXCEPTIONS_AND_TYPOS = self._constants.get("exceptions_and_typos", {})

    def _load_constants(self):
        if not self.CONSTANTS_JSON_PATH.exists():
            return {}
        try:
            with open(self.CONSTANTS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

settings = Settings()
