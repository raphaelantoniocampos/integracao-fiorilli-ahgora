from src.managers.data_manager import DataManager
from src.managers.download_manager import DownloadManager
from src.managers.task_manager import TaskManager
from src.utils.config import Config
from src.utils.ui import spinner, menu_table


def main():
    task_manager = TaskManager()
    data_manager = DataManager()
    download_manager = DownloadManager()

    while True:
        config = Config()
        tasks = task_manager.get_tasks()

        option = menu_table(tasks)
        match option.lower():
            case "baixar dados":
                download_manager.menu()

            case "analisar dados":
                data_manager.analyze()

            case "tarefas":
                task_manager.menu(tasks)

            case "configurações":
                config.menu()

            case "sair":
                spinner("Saindo")
                return


if __name__ == "__main__":
    try:
        main()
        exit(0)
    except KeyboardInterrupt:
        spinner("Saindo")
        exit(1)
