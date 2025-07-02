import time

import pyautogui
from pyperclip import copy
from rich import print

from src.models.key import wait_key_press, KEY_CONTINUE, KEY_NEXT, KEY_BACK, KEY_STOP
from src.models.task import Task
from src.tasks.task_runner import TaskRunner
from src.utils.ui import spinner


class AddEmployeesTask(TaskRunner):
    def __init__(self, task: Task):
        super().__init__(task)

    def run(self) -> None:
        df = self.task.data
        for i, series in df.iterrows():
            print(f"\n[bold gold1]{'-' * 15} NOVO FUNCIONÁRIO! {'-' * 15}[/bold gold1]")
            print(series)
            name = series.get("name")
            copy(name)
            print(f"Nome '{name}' copiado para a área de transferência!)")
            match wait_key_press([KEY_CONTINUE, KEY_NEXT, KEY_STOP]):
                case "continuar":
                    spinner("Continuando")
                    self._auto_new(series)
                case "próximo":
                    spinner("Continuando")
                case "sair":
                    self.exit_task()
                    spinner()
                    return

        print("[bold green]Não há mais novos funcionários![/bold green]")
        self.exit_task()

    def _auto_new(self, row):
        print(
            "Clique em [bright_blue]Novo Funcionário[/], clique no [bright_blue]Nome[/]"
        )
        match wait_key_press([KEY_CONTINUE, KEY_BACK]):
            case "voltar":
                spinner()
                return
        pyautogui.write(row["name"], interval=0.02)
        time.sleep(0.2)

        pyautogui.press("tab", presses=7, interval=0.005)
        time.sleep(0.2)

        pis_pasep = row["pis_pasep"]
        pyautogui.write(pis_pasep, interval=0.2)
        time.sleep(0.2)

        pyautogui.press("tab")
        time.sleep(0.2)

        spinner(
            wait_string="[gold1]Processando PIS-PASEP[/gold1]",
            wait_time=2,
        )
        formatted_pis_pasep = (
            f"{pis_pasep[:3]}.{pis_pasep[3:8]}.{pis_pasep[8:10]}-{pis_pasep[10]}"
        )
        print(f"PIS-PASEP: [gold1]{formatted_pis_pasep}[/]")

        wait_key_press(KEY_CONTINUE)
        print("[bold green]Continuando![/bold green]")

        pyautogui.press("tab")
        time.sleep(0.2)

        pyautogui.write(row["cpf"], interval=0.05)
        time.sleep(0.2)

        for i in range(5):
            pyautogui.hotkey("shift", "tab")
            time.sleep(0.005)

        pyautogui.write(row["birth_date"], interval=0.02)
        time.sleep(0.2)

        pyautogui.hotkey("shift", "tab")
        time.sleep(0.1)

        pyautogui.write(row["sex"], interval=0.02)
        time.sleep(0.2)

        pyautogui.press("tab", presses=19, interval=0.005)
        time.sleep(0.2)

        pyautogui.write("es", interval=0.02)
        time.sleep(0.2)

        pyautogui.press("tab")
        time.sleep(0.2)

        pyautogui.write(str(row["id"]), interval=0.02)
        time.sleep(0.2)

        pyautogui.press("tab", presses=2, interval=0.005)
        time.sleep(0.2)

        pyautogui.write(row["admission_date"], interval=0.02)
        time.sleep(0.2)

        pyautogui.press("tab", presses=3, interval=0.005)
        time.sleep(0.2)

        pyautogui.write("12345", interval=0.02)
        time.sleep(0.5)

        pyautogui.press("tab", presses=7, interval=0.005)
        time.sleep(0.2)

        pyautogui.write(row["position"], interval=0.02)
        time.sleep(0.2)

        pyautogui.press("tab", presses=2, interval=0.005)
        time.sleep(0.2)

        pyautogui.write(row["department"][:15], interval=0.02)
        time.sleep(0.2)

        pyautogui.press("tab", presses=3, interval=0.005)
        time.sleep(0.2)

        pyautogui.scroll(-350)
        time.sleep(0.2)

        pyautogui.press("space")
        time.sleep(0.2)

        print(f"Insira o Departamento\n[gold1]{row['department']}[/]")

        wait_key_press(KEY_NEXT)
