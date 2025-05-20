from pathlib import Path

from pandas import DataFrame
from rich import print

from src.utils.constants import DATA_DIR, DOWNLOADS_DIR


class FileManager:
    def move_downloads_to_data_dir(self):
        try:
            for file in DOWNLOADS_DIR.iterdir():
                if "trabalhador" in file.name.lower():
                    self.move_file(
                        source=file,
                        destination=DATA_DIR / "fiorilli" / "raw_employees.txt",
                    )
                elif "funcionarios" in file.name.lower():
                    self.move_file(
                        source=file,
                        destination=DATA_DIR / "ahgora" / "raw_employees.csv",
                    )
                elif "pontoafastamentos" in file.name.lower():
                    self.move_file(
                        source=file,
                        destination=DATA_DIR / "fiorilli" / "raw_absences.txt",
                    )
                elif "pontoferias" in file.name.lower():
                    self.move_file(
                        source=file,
                        destination=DATA_DIR / "fiorilli" / "raw_vacations.txt",
                    )
        except FileNotFoundError:
            DOWNLOADS_DIR.mkdir()

    @staticmethod
    def save_df(
        df: DataFrame,
        path: Path,
        header=True,
    ):
        df.to_csv(
            path,
            index=False,
            header=header,
            encoding="utf-8",
        )

    @staticmethod
    def file_name_to_file_path(file_name: str, raw: bool = True) -> Path:
        match file_name:
            case "ahgora_employees":
                return DATA_DIR / "ahgora" / "raw_employees.csv"
            case "fiorilli_employees":
                return DATA_DIR / "fiorilli" / "raw_employees.txt"
            case "absences":
                return DATA_DIR / "fiorilli" / "raw_absences.txt"

    def move_file(self, source: Path, destination: Path):
        if not destination.parent.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
        print(f"[bold green]Arquivo movido:[/bold green]{source.name} -> {destination}")
