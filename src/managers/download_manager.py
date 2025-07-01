from InquirerPy import inquirer

from src.browsers.ahgora_browser import AhgoraBrowser
from src.browsers.fiorilli_browser import FiorilliBrowser
from src.managers.data_manager import DataManager
from src.managers.file_manager import FileManager
from src.utils.ui import menu

DOWNLOAD_CHOICES = {
    "Funcionários Fiorilli": FiorilliBrowser.download_employees_data,
    "Funcionários Ahgora": AhgoraBrowser.download_employees_data,
    "Afastamentos": FiorilliBrowser.download_leaves_data,
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
        actions = [action for _, action in DOWNLOAD_CHOICES.items()]
        return self.start_downloads(actions)

    def select_download(self):
        action = menu(name="Escolher", choices=DOWNLOAD_CHOICES)
        if action.__name__ == "spinner":
            return action
        return self.start_downloads([action])

    def start_downloads(self, actions):
        if not inquirer.confirm(message="Continuar?", default=True).execute():
            return

        for download_option in actions:
            download_option()

        FileManager.move_downloads_to_data_dir()
        dm = DataManager()
        dm.analyze()

    @staticmethod
    def download_files(files):
        needed_downloads = []
        for file in files:
            if "raw_employees.txt" in file:
                needed_downloads.append(
                    FiorilliBrowser.download_employees_data,
                )
            if "raw_employees.csv" in file:
                needed_downloads.append(
                    AhgoraBrowser.download_employees_data,
                )
            if "raw_leaves.txt" or "raw_vacations.txt" in file:
                needed_downloads.append(
                    FiorilliBrowser.download_leaves_data,
                )
        for download in needed_downloads:
            download()
