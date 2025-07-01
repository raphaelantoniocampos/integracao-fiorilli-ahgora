import sys

from src.managers.data_manager import DataManager
from src.managers.download_manager import DownloadManager
from src.managers.file_manager import FileManager
from src.managers.task_manager import TaskManager
from src.utils.creds import Creds
from src.utils.config import Config
from src.utils.ui import main_menu, spinner, console
import time


def main():
    config = Config()
    if not config.status.working:
        if config.status.missing_directories:
            console.print(
                f"Criando diretórios.\n{config.status.missing_directories}",
            )
            time.sleep(1)
            FileManager.create_directories(
                directories=config.status.missing_directories,
            )
        if config.status.missing_vars:
            console.print(
                f"É necessária a configuração das variáveis de ambiente.\n{
                    config.status.missing_vars
                }",
            )
            time.sleep(1)
            Creds.create_vars(
                vars=config.status.missing_vars,
            )
        if config.status.missing_files:
            console.print(
                f"Arquivos necessários ausentes. Iniciando download\n{
                    config.status.missing_files
                }",
            )
            time.sleep(1)
            DownloadManager.download_files(
                files=config.status.missing_files,
            )
        print(config.status)
        return
        config = Config()

    task_manager = TaskManager()
    data_manager = DataManager()
    download_manager = DownloadManager()
    FileManager.setup()

    MENU_OPTIONS = {
        "Downloads": download_manager.open,
        "Dados": data_manager.open,
        "Tarefas": task_manager.open,
        "Configurações": config.open,
        "Sair": lambda: sys.exit(0),
    }

    while True:
        config.setup()
        tasks = task_manager.get_tasks()

        action = main_menu(
            tasks=tasks,
            choices=MENU_OPTIONS,
        )
        while callable(action):
            action = action()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        spinner("Saindo")
