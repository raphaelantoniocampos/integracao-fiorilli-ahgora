import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd


from src.managers.file_manager import FileManager
from src.managers.update_manager import UpdateManager
from src.utils.constants import (
    DATA_DIR,
    FIORILLI_DIR,
    TASKS_DIR,
    JSON_INIT_CONFIG,
)
from src.utils.creds import Creds
from src.utils.console import console
from src.utils.ui import menu, get_number

from dataclasses import dataclass


@dataclass
class Status:
    working: bool
    missing_vars: list
    missing_files: list


class Config:
    def __init__(self):
        self.setup()

    def open(self, result=" ") -> None:
        if not result:
            return
        self.setup()
        CONFIG_MENU_CHOICES = {
            "Alterar Headless Mode": self.toggle_headless_mode,
            "Alterar Número de Meses Retroativos - Afastamentos": self.change_leaves_months_ago,
            "Adicionar Afastamentos Manual": lambda: FileManager.copy_file(
                source=FIORILLI_DIR / "leaves.csv",
                destination=TASKS_DIR / "manual_leaves.csv",
            ),
            "Abrir arquivo de configurações": self.open_config_file,
            "Resetar credenciais": self.reset_creds,
        }

        self.update_time_since()
        console.log(result)
        header = self.config_header
        return menu(
            name="Configurações",
            header=header,
            choices=CONFIG_MENU_CHOICES,
        )

    def config_header(self, name):
        return console.print(f"""[bold cyan]{name}[/bold cyan]
[bold orange]Opções[/bold orange]
[cyan]•[/] [bold]Modo de Download Headless[/bold]: {self.headless_mode}
[cyan]•[/] [bold]Quantos meses atrás - Download de Afastamentos[/bold]: {
            self.leaves_months_ago
        }


[bold orange]Dados[/bold orange]
[cyan]•[/] [bold]Análise[/]: {self.last_analisys["datetime"]} ([bold]{
            self.last_analisys["time_since"]
        }[/] atrás)

[cyan]•[/] [bold]Downloads[/]:
  • Afastamentos - {self.last_download_leaves["datetime"]} ([bold]{
            self.last_download_leaves["time_since"]
        }[/] atrás)
  • Funcionários Fiorilli - {self.last_download_fiorilli["datetime"]} ([bold]{
            self.last_download_fiorilli["time_since"]
        }[/] atrás)
  • Funcionários Ahgora - {self.last_download_ahgora["datetime"]} ([bold]{
            self.last_download_ahgora["time_since"]
        }[/] atrás)
""")

    def setup(self):
        FileManager.setup()
        self.json_path: Path = DATA_DIR / "config.json"
        self.data: dict = self._load()
        Creds(required_vars=self.data.get("required_vars"))
        self.status = self.check_status()
        self.update_status()
        self.update_time_since()
        self.last_analisys = self.data.get("last_analisys")
        self.headless_mode = bool(self.data.get("headless_mode"))
        self.last_download_fiorilli = self.data.get("last_download")[
            "fiorilli_employees"
        ]
        self.last_download_ahgora = self.data.get("last_download")["ahgora_employees"]
        self.last_download_leaves = self.data.get("last_download")["leaves"]
        self.leaves_months_ago = int(self.data.get("leaves_months_ago"))
        self.generate_config_tasks()
        # UpdateManager.check_for_updates()

    def check_status(self):
        missing_vars = Creds.get_missing_vars(
            required_vars=self.data.get("required_vars")
        )
        missing_files = FileManager.get_missing_files()

        working = not any(missing_vars + missing_files)

        return Status(
            working=working,
            missing_vars=missing_vars,
            missing_files=[str(file) for file in missing_files],
        )

    def update_status(self):
        self._update(
            "status",
            "working",
            value=self.status.working,
        )
        self._update(
            "status",
            "missing_vars",
            value=self.status.missing_vars,
        )
        self._update(
            "status",
            "missing_files",
            value=self.status.missing_files,
        )

    def generate_config_tasks(self):
        missing_files_df = pd.DataFrame(self.status.missing_files)
        if not missing_files_df.empty:
            FileManager.save_df(
                df=missing_files_df,
                path=TASKS_DIR / "missing_files.csv",
            )
        missing_vars_df = pd.DataFrame(self.status.missing_vars)
        if not missing_vars_df.empty:
            FileManager.save_df(
                df=missing_vars_df,
                path=TASKS_DIR / "missing_vars.csv",
            )

    @staticmethod
    def update_last_analisys():
        now = datetime.now()
        last_analisys = {"datetime": now.strftime("%d/%m/%Y, %H:%M"), "time_since": now}
        Config()._update_analysis_time_since(last_analisys, now)

    def _load(self) -> dict:
        if self.json_path.exists():
            with open(self.json_path, "r") as f:
                return json.load(f)
        else:
            self.data = self._create()
            return self._update(
                "init_date", value=datetime.now().strftime("%d/%m/%Y, %H:%M")
            )

    def _read(self) -> dict:
        return self.data

    def _update(self, *keys, value=None) -> dict:
        data = self.data
        *path, last_key = keys

        for key in path:
            if key not in data or not isinstance(data[key], dict):
                data[key] = {}
            data = data[key]

        if isinstance(data.get(last_key), dict) and isinstance(value, dict):
            data[last_key].update(value)
        else:
            data[last_key] = value

        with open(self.json_path, "w") as f:
            json.dump(self.data, f, indent=4)

        return self.data

    def _create(self) -> dict:
        with open(self.json_path, "w") as f:
            json.dump(JSON_INIT_CONFIG, f, indent=4)
        return JSON_INIT_CONFIG

    def _delete(self, field: str, key: str) -> str:
        if field in self.data and key in self.data[field]:
            del self.data[field][key]
            with open(self.json_path, "w") as f:
                json.dump(self.data, f, indent=4)
            return f"Item '{key}' removido do campo '{field}'."
        else:
            return f"Item '{key}' não encontrado no campo '{field}'."

    def _format_timedelta(self, td: timedelta) -> str:
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m"

    def update_time_since(self) -> None:
        try:
            now = datetime.now()
            last_analisys = self.data.get("last_analisys")
            self._update_analysis_time_since(
                last_analisys,
                now,
            )

            last_download = self.data.get("last_download")
            self._update_downloads_time_since(
                last_download,
                "ahgora_employees",
                now,
            )
            self._update_downloads_time_since(
                last_download,
                "fiorilli_employees",
                now,
            )
            self._update_downloads_time_since(
                last_download,
                "leaves",
                now,
            )
        except FileNotFoundError:
            return

    def toggle_headless_mode(self):
        headless_mode = self.data.get("headless_mode")
        change_to = not headless_mode
        self._update("headless_mode", value=change_to)
        return f"Headless mode alterado para {change_to}"

    def change_leaves_months_ago(self):
        leaves_months_ago = get_number("Meses: (padrão: 2)", 1, 12)
        self._update("leaves_months_ago", value=leaves_months_ago)
        return f"Número de meses alterado para {leaves_months_ago}"

    def open_config_file(self):
        return subprocess.run(["explorer.exe", self.json_path])

    def reset_creds(self):
        env_file = Path(".env")
        if not env_file.exists():
            input("Abra o diretório fonte e execute com 'uv run main.py'")
            return
        return subprocess.run(["explorer.exe", env_file])

    def _update_analysis_time_since(self, last_analisys: dict, now: timedelta) -> None:
        if last_analisys["datetime"]:
            last_analisys_dt = datetime.strptime(
                last_analisys["datetime"], "%d/%m/%Y, %H:%M"
            )
            time_since_last_analisys = now - last_analisys_dt
            last_analisys["time_since"] = self._format_timedelta(
                time_since_last_analisys
            )
            self._update("last_analisys", value=last_analisys)

    def _update_downloads_time_since(
        self, last_download: dict, file_name: str, now: timedelta
    ) -> None:
        file_last_download = last_download.get(file_name)

        file_last_download["datetime"] = self._get_last_download(file_name)

        last_download_dt = datetime.strptime(
            file_last_download["datetime"], "%d/%m/%Y, %H:%M"
        )
        time_since_last_download = now - last_download_dt
        file_last_download["time_since"] = self._format_timedelta(
            time_since_last_download
        )

        self._update("last_download", file_name, value=file_last_download)

    def _get_last_download(self, file_name: str) -> str:
        file_path = FileManager.file_name_to_file_path(file_name)

        return datetime.strftime(
            datetime.fromtimestamp(file_path.stat().st_mtime),
            "%d/%m/%Y, %H:%M",
        )

    def __str__(self):
        str_return = ""
        for key, value in self._read().items():
            str_return += f"{key}: {value}\n"

        return str_return
