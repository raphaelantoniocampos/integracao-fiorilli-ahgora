from pathlib import Path

from pandas import DataFrame

from src.managers.data_manager import DataManager
from src.models.task import Task
from src.tasks.add_employees_task import AddEmployeesTask
from src.tasks.add_leaves_task import AddLeavesTask
from src.tasks.remove_employees_task import RemoveEmployeesTask
from src.tasks.update_employees_task import UpdateEmployeesTask
from src.utils.constants import TASKS_DIR
from src.utils.ui import menu


class TaskManager:
    def open(self):
        tasks = self.get_tasks()
        tasks_choices = {task.option: task for task in tasks if not task.data.empty}

        task = menu(name="Tarefas", choices=tasks_choices)
        if not isinstance(task, Task):
            return task
        return lambda: self.run_task(task)

    def run_task(self, task: Task):
        match task.name:
            case "add_employees":
                AddEmployeesTask(task)
            case "remove_employees":
                RemoveEmployeesTask(task)
            case "update_employees":
                UpdateEmployeesTask(task)
            case "add_leaves":
                AddLeavesTask(task)
            case "manual_leaves":
                AddLeavesTask(task)

    @staticmethod
    def get_tasks() -> list[Task]:
        tm = TaskManager()
        return [
            tm.name_to_task("add_employees"),
            tm.name_to_task("remove_employees"),
            tm.name_to_task("update_employees"),
            tm.name_to_task("add_leaves"),
            tm.name_to_task("manual_leaves"),
            tm.name_to_task("missing_files"),
            tm.name_to_task("missing_vars"),
            tm.name_to_task("analyze"),
        ]

    def name_to_task(self, name: str) -> Task:
        path = self._get_path(name)
        data = self._get_data(path)
        option = self._get_option(name, data)

        task = Task(
            name=name,
            path=path,
            data=data,
            option=option,
        )
        return task

    def _get_data(self, path) -> DataFrame | None:
        data_manager = DataManager()
        if isinstance(path, str):
            return DataFrame()
        if not path.exists():
            return DataFrame()
        return data_manager.read_csv(path)

    def _get_path(self, name: str) -> Path:
        return TASKS_DIR / f"{name}.csv"

    def _get_option(self, name: str, data: DataFrame) -> str:
        match name:
            case "add_employees":
                return "" if data.empty else f"Adicionar {len(data)} funcionários"

            case "remove_employees":
                return "" if data.empty else f"Remover {len(data)} funcionários"

            case "update_employees":
                return "" if data.empty else f"Atualizar {len(data)} funcionários"

            case "add_leaves":
                return "" if data.empty else f"Adicionar +/- {len(data)} afastamentos"

            case "manual_leaves":
                return "" if data.empty else "Adicionar Afastamentos Manual"

            case "missing_files":
                file_paths = [Path(file[0]) for _, file in data.iterrows()]
                files = []
                for file in file_paths:
                    file_splits = str(file).split("\\")
                    files.append(f"{file_splits[-2]}\\{file_splits[-1]}")
                return "" if data.empty else f"Baixar arquivos\n{files}"

            case "missing_vars":
                return (
                    ""
                    if data.empty
                    else f"Configurar variáveis de ambiente\n{[var[0] for _, var in data.iterrows()]}"
                )

            case "analyze":
                return "" if data.empty else "Analisar dados"
