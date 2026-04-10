import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.infrastructure.automation.web.ahgora_browser import AhgoraBrowser
from app.core.file_manager import FileManager


def test_ahgora_download():
    """
    Downloads Ahgora CSV specifically.
    """
    # Force headless=True or False as desired.
    # Since we're running locally/Docker, let's use the .env configurations.
    headless = os.getenv("HEADLESS_MODE", "True").lower() == "true"

    ahgora_user = os.getenv("AHGORA_USER")
    ahgora_password = os.getenv("AHGORA_PASSWORD")
    ahgora_company = os.getenv("AHGORA_COMPANY")
    ahgora_url = os.getenv("AHGORA_URL")

    print(f"Starting Ahgora download test (headless={headless})...")
    print(f"Using company {ahgora_company} and user {ahgora_user}")

    FileManager.setup()  # Ensure directories exist
    FileManager.cleanup()  # Optional: clear old downloads

    browser = AhgoraBrowser(
        ahgora_password=ahgora_password,
        ahgora_user=ahgora_user,
        ahgora_company=ahgora_company,
        ahgora_url=ahgora_url,
        headless=headless,
    )

    try:
        browser.download_employees()
        print("Scraping finished. Moving file...")
        FileManager.move_downloads_to_data_dir()

        csv_file = Path("data/ahgora_employees.csv")
        if csv_file.exists():
            with open(csv_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                print(
                    f"\n✅ Download successful! File ahgora_employees.csv has {len(lines)} lines."
                )
        else:
            print("\n❌ File ahgora_employees.csv was not found after move!")
    except Exception as e:
        print(f"Error during download: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_ahgora_download()
