import sys
from src.managers.data_manager import DataManager
from src.managers.download_manager import DownloadManager
from src.managers.file_manager import FileManager
from src.managers.task_manager import TaskManager
from src.utils.config import Config
from src.utils.ui import main_menu, spinner

MAIN_MENU_CHOICES = [
    "Downloads",
    "Dados",
    "Tarefas",
    "Configurações",
    "Sair",
]


def main():
    task_manager = TaskManager()
    data_manager = DataManager()
    download_manager = DownloadManager()
    FileManager.setup()

    MENU_ACTIONS = {
        # Downloads
        MAIN_MENU_CHOICES[0]: lambda: download_manager.menu(
            MAIN_MENU_CHOICES[0],
        ),
        # Dados
        MAIN_MENU_CHOICES[1]: lambda: data_manager.menu(
            MAIN_MENU_CHOICES[1],
        ),
        # Tarefas
        MAIN_MENU_CHOICES[2]: lambda: task_manager.menu(
            MAIN_MENU_CHOICES[2],
        ),
        # Configurações
        MAIN_MENU_CHOICES[3]: lambda: config.menu(
            MAIN_MENU_CHOICES[3],
        ),
        # Sair
        MAIN_MENU_CHOICES[4]: lambda: sys.exit(0),
    }

    while True:
        config = Config()
        tasks = task_manager.get_tasks()

        main_menu(
            tasks=tasks,
            choices=MENU_ACTIONS,
        )()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        spinner("Saindo")
