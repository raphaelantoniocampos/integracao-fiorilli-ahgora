from pathlib import Path

from InquirerPy import inquirer
from pandas import DataFrame
from rich.panel import Panel

from src.managers.data_manager import DataManager
from src.models.task import Task
from src.tasks.add_absences_task import AddAbsencesTask
from src.tasks.add_employees_task import AddEmployeesTask
from src.tasks.remove_employees_task import RemoveEmployeesTask
from src.tasks.update_employees_task import UpdateEmployeesTask
from src.utils.constants import DATA_DIR, INQUIRER_KEYBINDINGS
from src.utils.ui import console, spinner


class TaskManager:
    def menu(self, tasks: list[Task]):
        ()
        console.print(
            Panel.fit(
                "Escolher Tarefas",
                style="bold cyan",
            )
        )
        choice = {task.option: task for task in tasks if not task.df.empty}
        choice["Voltar"] = ""

        option = inquirer.rawlist(
            message="Selecione uma tarefa",
            choices=choice.keys(),
            keybindings=INQUIRER_KEYBINDINGS,
        ).execute()

        if "Voltar" in option:
            spinner()
            return

        self.run_task(choice[option])

    def run_task(self, task: Task):
        match task.name:
            case "add_employees":
                AddEmployeesTask(task)
            case "remove_employees":
                RemoveEmployeesTask(task)
            case "update_employees":
                UpdateEmployeesTask(task)
            case "add_absences":
                AddAbsencesTask(task)

    @staticmethod
    def get_tasks() -> list[Task]:
        tm = TaskManager()
        return [
            tm.name_to_task("add_employees"),
            tm.name_to_task("remove_employees"),
            tm.name_to_task("update_employees"),
            tm.name_to_task("add_absences"),
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
        match name:
            case "add_employees":
                return DATA_DIR / "tasks" / "new_employees.csv"
            case "remove_employees":
                return DATA_DIR / "tasks" / "dismissed_employees.csv"
            case "update_employees":
                return DATA_DIR / "tasks" / "changed_employees.csv"
            case "add_absences":
                return DATA_DIR / "tasks" / "new_absences.csv"

    def _get_option(self, name: str, df: DataFrame) -> str:
        if df.empty:
            return ""

        match name:
            case "add_employees":
                return f"Adicionar {len(df)} funcionários"

            case "remove_employees":
                return f"Remover {len(df)} funcionários"

            case "update_employees":
                return f"Atualizar {len(df)} funcionários"

            case "add_absences":
                return f"Adicionar (+/- {len(df)}) afastamentos"
