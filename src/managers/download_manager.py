from InquirerPy import inquirer
from rich.panel import Panel

from src.browsers.ahgora_browser import AhgoraBrowser
from src.browsers.fiorilli_browser import FiorilliBrowser
from src.managers.data_manager import DataManager
from src.managers.file_manager import FileManager
from src.utils.constants import INQUIRER_KEYBINDINGS
from src.utils.ui import console, spinner


class DownloadManager:
    DOWNLOAD_OPTIONS = {
        "Afastamentos": FiorilliBrowser.download_absences_data,
        "Funcionários Ahgora": AhgoraBrowser.download_employees_data,
        "Funcionários Fiorilli": FiorilliBrowser.download_employees_data,
    }

    def menu(self):
        console.print(
            Panel.fit(
                "BAIXAR DADOS",
                style="bold cyan",
            )
        )
        choices = [option for option in self.DOWNLOAD_OPTIONS]
        choices.append("Voltar")

        answers = inquirer.checkbox(
            message="Selecione as opções de download",
            choices=choices,
            keybindings=INQUIRER_KEYBINDINGS,
        ).execute()

        selected_options = []
        if choices[-1] in answers:
            spinner()
            return

        for answer in answers:
            selected_options.append(answer)

        proceed = inquirer.confirm(message="Continuar?", default=True).execute()
        if not proceed:
            return

        self.run(selected_options)
        DataManager().analyze()

    def run(self, selected_options):
        for option in selected_options:
            fun = self.DOWNLOAD_OPTIONS[option]
            fun()

        self._move_files_to_data_dir()

    def _move_files_to_data_dir(self):
        file_manager = FileManager()
        file_manager.move_downloads_to_data_dir()
