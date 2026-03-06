from pathlib import Path

import shutil
import pandas as pd

from app.core.settings import settings


class FileManager:
    TASKS_DIR = settings.BASE_DIR / "tasks"

    @classmethod
    def setup(cls):
        """Ensure all required directories exist."""
        directories = [
            settings.DATA_DIR,
            settings.DOWNLOADS_DIR,
            cls.TASKS_DIR,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def move_downloads_to_data_dir(cls):
        """Move files from downloads folder to their respective data directories."""
        if not settings.DOWNLOADS_DIR.exists():
            return

        for file in settings.DOWNLOADS_DIR.iterdir():
            if not file.is_file():
                continue

            file_name_lower = file.name.lower()
            if "trabalhador" in file_name_lower:
                cls.move_file(file, settings.DATA_DIR / "fiorilli_employees.txt")
            elif "funcionarios" in file_name_lower:
                cls.move_file(file, settings.DATA_DIR / "ahgora_employees.txt")
            elif "pontoafastamentos" in file_name_lower:
                cls.move_file(file, settings.DATA_DIR / "raw_leaves.txt")
            elif "pontoferias" in file_name_lower:
                cls.move_file(file, settings.DATA_DIR / "raw_vacations.txt")

    @staticmethod
    def move_file(source: Path, destination: Path):
        """Move a file and ensure the destination parent exists."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        shutil.move(str(source), str(destination))

    @staticmethod
    def save_df(df: pd.DataFrame, path: Path, header=True, columns=None):
        """Save a pandas DataFrame to CSV."""
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(
            path,
            index=False,
            encoding="utf-8",
            header=header,
            columns=columns,
        )

    @staticmethod
    def cleanup():
        """Delete old files in the download folder"""
        if not settings.DOWNLOADS_DIR.exists():
            return
        for file in settings.DOWNLOADS_DIR.iterdir():
            if not file.is_file():
                continue
            file.unlink()
