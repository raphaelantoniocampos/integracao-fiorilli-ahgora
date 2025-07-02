import sys

from src.managers.data_manager import DataManager
from src.managers.download_manager import DownloadManager
from src.managers.file_manager import FileManager
from src.managers.task_manager import TaskManager
from src.utils.config import Config
from src.utils.ui import main_menu, spinner


def main():
    FileManager.setup()
    config = Config()

    task_manager = TaskManager()
    data_manager = DataManager()
    download_manager = DownloadManager()

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
    except Exception as err:
        input(f"Safe exit: {err}")
