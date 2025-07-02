import subprocess
from abc import ABC, abstractmethod

from InquirerPy import inquirer
from pyperclip import copy
from rich import print
from rich.panel import Panel

from src.managers.data_manager import DataManager
from src.models.key import wait_key_press, KEY_CONTINUE
from src.models.task import Task
from src.utils.ui import console, spinner


class TaskRunner(ABC):
    def __init__(self, task: Task):
        self.task = task
        if self.task.df.empty:
            return
        return self.menu()

    def menu(self) -> None:
        """Displays the task menu"""
        console.log(
            Panel.fit(
                self.task.option,
                style="bold cyan",
            )
        )

        choose_itens = inquirer.confirm(
            message="Ver e escolher itens da lista?", default=False
        ).execute()
        if choose_itens:
            itens = self._choose_itens()
            if not itens:
                return
            ids = [item[0] for item in itens]
            self.task.df = DataManager.filter_df(self.task.df, ids)

        if inquirer.confirm(message="Iniciar?", default=True).execute():
            url = self.task.url
            open_browser_prompt = inquirer.confirm(
                message="Abrir navegador?", default=True
            ).execute()
            if open_browser_prompt:
                self._open_browser(url)
                self.run()
                return
            print(f"URL '{url}' copiada para a área de transferência!)")
            copy(url)
            wait_key_press(KEY_CONTINUE)
            self.run()

        spinner()

    @abstractmethod
    def run() -> None:
        """Runs the task"""

    def exit_task(self):
        confirm_exit = inquirer.confirm(
            message="Marcar como finalizado?",
            default=True,
        ).execute()

        if confirm_exit:
            self.task.path.unlink()

    def _choose_itens(
        self,
    ):
        return inquirer.fuzzy(
            message="Select actions:",
            choices=self.task.df.values.tolist(),
            keybindings={
                "answer": [
                    {"key": "enter"},
                ],
                "interrupt": [
                    {"key": "c-c"},
                    {"key": "c-e"},
                ],
                "skip": [
                    {"key": "c-z"},
                    {"key": "escape"},
                ],
                "down": [
                    {"key": "down"},
                ],
                "up": [
                    {"key": "up"},
                ],
                "toggle": [
                    {"key": "space"},
                ],
            },
            mandatory=False,
            multiselect=True,
            border=True,
        ).execute()

    def _open_browser(self, url: str) -> None:
        subprocess.run(["explorer.exe", url])
