import os
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


settings = Settings()
