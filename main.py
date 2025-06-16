from src.managers.data_manager import DataManager
from src.managers.download_manager import DownloadManager
from src.managers.task_manager import TaskManager
from src.managers.file_manager import FileManager
from src.utils.config import Config
from src.utils.constants import MAIN_MENU_OPTIONS
from src.utils.ui import console, menu_table, spinner


def main():
    task_manager = TaskManager()
    data_manager = DataManager()
    download_manager = DownloadManager()
    FileManager.setup()

    MENU_ACTIONS = {
        # Downloads
        MAIN_MENU_OPTIONS[0]: lambda: download_manager.menu(
            MAIN_MENU_OPTIONS[0],
        ),
        # Dados
        MAIN_MENU_OPTIONS[1]: lambda: data_manager.menu(
            MAIN_MENU_OPTIONS[1],
        ),
        # Tarefas
        MAIN_MENU_OPTIONS[2]: lambda: task_manager.menu(
            MAIN_MENU_OPTIONS[2],
        ),
        # Configurações
        MAIN_MENU_OPTIONS[3]: lambda: config.menu(
            MAIN_MENU_OPTIONS[3],
        ),
        # Sair
        MAIN_MENU_OPTIONS[4]: lambda: exit_program(),
    }

    while True:
        console.clear()
        config = Config()
        tasks = task_manager.get_tasks()

        option = menu_table(tasks)
        action = MENU_ACTIONS.get(option)
        action()


def exit_program():
    raise KeyboardInterrupt()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        spinner("Saindo")
