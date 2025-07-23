import shutil
from pathlib import Path

from pandas import DataFrame
from src.utils.ui import console

from src.utils.constants import (
    DATA_DIR,
    DOWNLOADS_DIR,
    TASKS_DIR,
    FIORILLI_DIR,
    AHGORA_DIR,
)

DIRECTORIES = [DATA_DIR, DOWNLOADS_DIR, TASKS_DIR, FIORILLI_DIR, AHGORA_DIR]


class FileManager:
    @staticmethod
    def setup():
        if missing_dirs := FileManager.get_missing_directories():
            FileManager.create_directories(missing_dirs)
        FileManager.move_downloads_to_data_dir()
        FileManager.cleanup()

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
        console.log(
            f"[bold green]Arquivo movido:[/bold green]{source.name} -> {destination}"
        )

    @staticmethod
    def copy_file(source: Path, destination: Path):
        shutil.copy2(source, destination)

    @staticmethod
    def rename_file(file_path: Path, new_name: str):
        file_path.replace(Path(file_path.parent / new_name))

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
    def get_missing_directories():
        missing_dirs = []
        for dir in DIRECTORIES:
            if not dir.exists():
                missing_dirs.append(dir)
        return missing_dirs

    @staticmethod
    def create_directories(directories=DIRECTORIES):
        for dir in directories:
            if not isinstance(dir, Path):
                dir = Path(dir)
            console.log(f"Criando diretório: {dir.name}")
            dir.mkdir(exist_ok=True)

    @staticmethod
    def get_missing_files():
        files_to_check = [
            Path(FIORILLI_DIR / "raw_employees.txt"),
            Path(AHGORA_DIR / "raw_employees.csv"),
            Path(FIORILLI_DIR / "raw_leaves.txt"),
            Path(FIORILLI_DIR / "raw_vacations.txt"),
        ]
        missing_files = []
        for file in files_to_check:
            if not file.exists():
                missing_files.append(file)
        return missing_files

    @staticmethod
    def cleanup():
        manual_leaves_path = TASKS_DIR / "manual_leaves.csv"
        missing_files = TASKS_DIR / "missing_files.csv"
        missing_vars = TASKS_DIR / "missing_vars.csv"

        files = [manual_leaves_path, missing_files, missing_vars]
        for file in files:
            if file.exists():
                file.unlink()
