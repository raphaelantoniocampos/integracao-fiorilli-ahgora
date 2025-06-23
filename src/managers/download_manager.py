from InquirerPy import inquirer

from src.browsers.ahgora_browser import AhgoraBrowser
from src.browsers.fiorilli_browser import FiorilliBrowser
from src.managers.data_manager import DataManager
from src.managers.file_manager import FileManager
from src.utils.ui import menu

DOWNLOAD_ACTIONS = {
    "Afastamentos": FiorilliBrowser.download_leaves_data,
    "Funcionários Ahgora": AhgoraBrowser.download_employees_data,
    "Funcionários Fiorilli": FiorilliBrowser.download_employees_data,
}


class DownloadManager:
    def open(self):
        return menu(
            name="Downloads",
            choices={
                "Baixar tudo": self.download_all,
                "Escolher": self.select_download,
            },
        )

    def download_all(self):
        options = [action for _, action in DOWNLOAD_ACTIONS.items()]
        self.start_downloads(options)

    def select_download(self):
        option = menu(name="Escolher", choices=DOWNLOAD_ACTIONS)
        if option.__name__ == "spinner":
            return option()
        self.start_downloads([option])

    def start_downloads(self, options):
        if not inquirer.confirm(message="Continuar?", default=True).execute():
            return

        for download_option in options:
            download_option()

        FileManager.move_downloads_to_data_dir()
        dm = DataManager()
        dm.analyze()
