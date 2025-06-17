from InquirerPy import inquirer
from rich.panel import Panel

from src.browsers.ahgora_browser import AhgoraBrowser
from src.browsers.fiorilli_browser import FiorilliBrowser
from src.managers.data_manager import DataManager
from src.managers.file_manager import FileManager
from src.utils.constants import INQUIRER_KEYBINDINGS
from src.utils.ui import console, spinner

DOWNLOAD_MESSAGE = "Selecione as opções de download"


class DownloadManager:
    DOWNLOAD_ACTIONS = {
        "Afastamentos": lambda: FiorilliBrowser.download_leaves_data(),
        "Funcionários Ahgora": lambda: AhgoraBrowser.download_employees_data(),
        "Funcionários Fiorilli": lambda: FiorilliBrowser.download_employees_data(),
        "Voltar": lambda: None,
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
            selected_actions = []
            match inquirer.rawlist(
                message=DOWNLOAD_MESSAGE,
                choices=choices,
                default=choices[0],
                keybindings=INQUIRER_KEYBINDINGS,
            ).execute():
                case "Baixar tudo":
                    selected_actions = [
                        action for _, action in self.DOWNLOAD_ACTIONS.items()
                    ][:-1]
                    break
                case "Escolher":
                    choices = [option for option in self.DOWNLOAD_ACTIONS.keys()]

                    option = inquirer.rawlist(
                        message=DOWNLOAD_MESSAGE,
                        choices=choices,
                        keybindings=INQUIRER_KEYBINDINGS,
                    ).execute()

                    selected = self.DOWNLOAD_ACTIONS.get(option)

                    if not selected():
                        spinner()
                        continue

                    selected_actions.append(selected)
                    break
                case "Voltar":
                    spinner()
                    return

        if not inquirer.confirm(message="Continuar?", default=True).execute():
            return

        for action in selected_actions:
            action()

        FileManager.move_downloads_to_data_dir()
        dm = DataManager()
        dm.analyze()
