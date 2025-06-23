from pathlib import Path

from pandas import DataFrame

from src.managers.data_manager import DataManager
from src.models.task import Task
from src.tasks.add_leaves_task import AddLeavesTask
from src.tasks.add_employees_task import AddEmployeesTask
from src.tasks.remove_employees_task import RemoveEmployeesTask
from src.tasks.update_employees_task import UpdateEmployeesTask
from src.utils.constants import TASKS_DIR
from src.utils.ui import menu


class TaskManager:
    def open(self):
        tasks = self.get_tasks()
        tasks_choices = {task.option: task for task in tasks if not task.df.empty}

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
        ]

    def name_to_task(self, name: str) -> Task:
        path = self._get_path(name)
        df = self._get_df(path)
        option = self._get_option(name, df)

        task = Task(
            name=name,
            path=path,
            df=df,
            option=option,
        )
        return task

    def _get_df(self, path) -> DataFrame | None:
        data_manager = DataManager()
        if isinstance(path, str):
            return DataFrame()
        if not path.exists():
            return DataFrame()
        return data_manager.read_csv(path)

    def _get_path(self, name: str) -> Path:
        return TASKS_DIR / f"{name}.csv"

    def _get_option(self, name: str, df: DataFrame) -> str:
        match name:
            case "add_employees":
                return "" if df.empty else f"Adicionar {len(df)} funcionários"

            case "remove_employees":
                return "" if df.empty else f"Remover {len(df)} funcionários"

            case "update_employees":
                return "" if df.empty else f"Atualizar {len(df)} funcionários"

            case "add_leaves":
                return "" if df.empty else f"Adicionar +/- {len(df)} afastamentos"

            case "manual_leaves":
                return "" if df.empty else "Adicionar Afastamentos Manual"
