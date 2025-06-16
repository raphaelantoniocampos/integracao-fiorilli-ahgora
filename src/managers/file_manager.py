from pathlib import Path

from pandas import DataFrame
from rich import print

from src.utils.constants import (
    DATA_DIR,
    DOWNLOADS_DIR,
    TASKS_DIR,
    FIORILLI_DIR,
    AHGORA_DIR,
)


class FileManager:
    @staticmethod
    def move_downloads_to_data_dir():
        for file in DOWNLOADS_DIR.iterdir():
            if "trabalhador" in file.name.lower():
                FileManager.move_file(
                    source=file,
                    destination=FIORILLI_DIR / "raw_employees.txt",
                )
            elif "funcionarios" in file.name.lower():
                FileManager.move_file(
                    source=file,
                    destination=AHGORA_DIR / "raw_employees.csv",
                )
            elif "pontoafastamentos" in file.name.lower():
                FileManager.move_file(
                    source=file,
                    destination=FIORILLI_DIR / "raw_leaves.txt",
                )
            elif "pontoferias" in file.name.lower():
                FileManager.move_file(
                    source=file,
                    destination=FIORILLI_DIR / "raw_vacations.txt",
                )

    @staticmethod
    def move_file(source: Path, destination: Path):
        if not destination.parent.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
        print(f"[bold green]Arquivo movido:[/bold green]{source.name} -> {destination}")

    @staticmethod
    def save_df(
        df: DataFrame,
        path: Path,
        header=True,
        columns=None,
    ):
        df.to_csv(
            path,
            index=False,
            encoding="utf-8",
            header=header,
            columns=columns,
        )

    @staticmethod
    def file_name_to_file_path(file_name: str, raw: bool = True) -> Path:
        match file_name:
            case "ahgora_employees":
                return AHGORA_DIR / "raw_employees.csv"
            case "fiorilli_employees":
                return FIORILLI_DIR / "raw_employees.txt"
            case "leaves":
                return FIORILLI_DIR / "raw_leaves.txt"

    @staticmethod
    def check_dirs():
        dirs_to_check = [DATA_DIR, DOWNLOADS_DIR, TASKS_DIR, FIORILLI_DIR, AHGORA_DIR]

        for dir in dirs_to_check:
            dir.mkdir(exist_ok=True)
