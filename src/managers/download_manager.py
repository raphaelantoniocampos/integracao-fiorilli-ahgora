from InquirerPy import inquirer
from rich.panel import Panel

from src.browsers.ahgora_browser import AhgoraBrowser
from src.browsers.fiorilli_browser import FiorilliBrowser
from src.managers.data_manager import DataManager
from src.managers.file_manager import FileManager as file_manager
from src.utils.constants import INQUIRER_KEYBINDINGS
from src.utils.ui import console, spinner

DOWNLOAD_MESSAGE = "Selecione as opções de download"


class DownloadManager:
    DOWNLOAD_OPTIONS = {
        "Afastamentos": FiorilliBrowser.download_leaves_data,
        "Funcionários Ahgora": AhgoraBrowser.download_employees_data,
        "Funcionários Fiorilli": FiorilliBrowser.download_employees_data,
    }

    def menu(self, name):
        console.print(
            Panel.fit(
                name.upper(),
                style="bold cyan",
            )
        )

        while True:
            choices = [
                "Baixar tudo",
                "Escolher",
                "Voltar",
            ]
            answer = inquirer.rawlist(
                message=DOWNLOAD_MESSAGE,
                choices=choices,
                default=choices[0],
                keybindings=INQUIRER_KEYBINDINGS,
            ).execute()
            match answer:
                case "Baixar tudo":
                    selected_options = [option for option in self.DOWNLOAD_OPTIONS]
                    break
                case "Escolher":
                    choices = [option for option in self.DOWNLOAD_OPTIONS]
                    choices.append("Voltar")

                    answers = inquirer.checkbox(
                        message=DOWNLOAD_MESSAGE,
                        choices=choices,
                        keybindings=INQUIRER_KEYBINDINGS,
                    ).execute()

                    selected_options = []
                    if choices[-1] in answers:
                        spinner()
                        continue

                    for answer in answers:
                        selected_options.append(answer)
                    break
                case "Voltar":
                    spinner()
                    return

        proceed = inquirer.confirm(message="Continuar?", default=True).execute()
        if not proceed:
            return

        self.run(selected_options)

    def run(self, selected_options):
        for option in selected_options:
            fun = self.DOWNLOAD_OPTIONS[option]
            fun()
        self._move_files_to_data_dir()
        dm = DataManager()
        dm.analyze()

    def _move_files_to_data_dir(self):
        file_manager.move_downloads_to_data_dir()
