import time

import pyautogui
from InquirerPy import inquirer
from pyperclip import copy
from rich import print

from src.models.key import Key, wait_key_press
from src.models.task import Task
from src.tasks.task_runner import TaskRunner
from src.utils.ui import spinner


class UpdateEmployeesTask(TaskRunner):
    KEY_CONTINUE = Key("F2", "green", "continuar")
    KEY_POSITION = Key("F1", "cyan", "escrever o cargo")
    KEY_DEPARTMENT = Key("F2", "violet", "escrever o departamento")
    KEY_NEXT = Key("F3", "yellow", "próximo")
    KEY_STOP = Key("F4", "red", "sair")

    def __init__(self, task: Task):
        super().__init__(task)

    def run(self):
        df = self.task.df

        for i, series in df.iterrows():
            name = series["name_fiorilli"]
            id = series["id"]

            position_changed = (
                series["position_fiorilli_norm"] != series["position_ahgora_norm"]
            )
            department_changed = (
                series["department_fiorilli_norm"] != series["department_ahgora_norm"]
            )

            position_fiorilli = series["position_fiorilli"]
            position_ahgora = series["position_ahgora"]
            department_fiorilli = series["department_fiorilli"]
            department_ahgora = series["department_ahgora"]

            changes = []
            if position_changed:
                changes.append("[cyan]CARGO[/]")
            if department_changed:
                changes.append("[violet]DEPARTAMENTO[/]")

            print(
                f"\n[bold yellow]{'-' * 15} FUNCIONÁRIO ALTERADO! {'-' * 15}[/bold yellow]"
            )
            print(f"{name} - {id}")
            print(f"Alterar {' e '.join(changes)}")
            print(f"Antigo Cargo (Ahgora): {position_ahgora}")
            print(
                f"Novo Cargo (Fiorilli): {f'[cyan]{position_fiorilli}[/]' if '[cyan]CARGO[/]' in changes else f'{position_fiorilli}'}"
            )
            print(f"Antigo Departamento (Ahgora): [bold]{department_ahgora}[/bold]")
            print(
                f"Novo Departamento (Fiorilli): {f'[violet]{department_fiorilli}[/]' if '[violet]DEPARTAMENTO[/]' in changes else f'{department_fiorilli}'}"
            )
            print("\n")
            copy(name)
            print(f"(Nome '{name}' copiado para a área de transferência!)")

            while True:
                match wait_key_press(
                    [
                        self.KEY_POSITION,
                        self.KEY_DEPARTMENT,
                        self.KEY_NEXT,
                        self.KEY_STOP,
                    ]
                ):
                    case "escrever o cargo":
                        copy(position_fiorilli)
                        pyautogui.write(position_fiorilli, interval=0.02)
                        time.sleep(0.5)
                    case "escrever o departamento":
                        copy(department_fiorilli)
                        pyautogui.write(department_fiorilli, interval=0.02)
                        time.sleep(0.5)
                    case "próximo":
                        spinner("Continuando")
                        break
                    case "sair":
                        self.exit_task()
                        spinner()
                        return

                if not inquirer.confirm(message="Repetir", default=False).execute():
                    break

        print("[bold green]Não há mais cargos para alterar![/bold green]")
        self.exit_task()
