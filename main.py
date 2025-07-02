import sys

from src.managers.data_manager import DataManager
from src.managers.download_manager import DownloadManager
from src.managers.file_manager import FileManager
from src.managers.task_manager import TaskManager
from src.utils.config import Config
from src.utils.ui import console, main_menu, spinner


def main():
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

# def get_config():
#     console.log("[bold green]Iniciando configuração...")
#     config = Config()
#     while not config.status.working:
#         console.log("Problemas encontrados:")
#         if config.status.missing_directories:
#             dirs = config.status.missing_directories
#             console.log(f"{len(dirs)} diretórios necessários.")
#
#             time.sleep(1)
#             FileManager.create_directories(
#                 directories=dirs,
#             )
#         if config.status.missing_vars:
#             vars = config.status.missing_vars
#             console.log(f"{len(vars)} variáveis de ambiente necessárias.")
#
#             time.sleep(1)
#             Creds.create_vars(
#                 vars=vars,
#             )
#         if config.status.missing_files:
#             files = config.status.missing_files
#             console.log(f"{len(files)} arquivos necessários.")
#             for file in files:
#                 console.log(Path(file).name)
#             time.sleep(1)
#         config = Config()
#     return config


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        spinner("Saindo")
    except Exception as e:
        console.log(f"Erro não tratado: \n[red]{repr(e)}\n[/]")
        input()
