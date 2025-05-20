import time

from pyperclip import copy
from rich import print

from src.models.key import Key, wait_key_press
from src.models.task import Task
from src.tasks.task_runner import TaskRunner
from src.utils.ui import spinner


class RemoveEmployeesTask(TaskRunner):
    KEY_CONTINUE = Key("F2", "green", "continuar")
    KEY_NEXT = Key("F3", "yellow", "próximo")
    KEY_STOP = Key("F4", "red3", "sair")

    def __init__(self, task: Task):
        super().__init__(task)

    def run(self):
        df = self.task.df
        for i, series in df.iterrows():
            print(
                f"\n[bold yellow]{'-' * 15} FUNCIONÁRIO DESLIGADO! {'-' * 15}[/bold yellow]"
            )
            print(series)
            name = series["name"]
            copy(name)
            print("\nProcure o nome e clique no [bold red]x[/bold red]")
            print(f"(Nome '{name}' copiado para a área de transferência!)\n")
            match wait_key_press([self.KEY_CONTINUE, self.KEY_NEXT, self.KEY_STOP]):
                case "continuar":
                    spinner("Continuando")
                    date = series["dismissal_date"]
                    print(
                        f"(Data de Desligamento '{date}' copiado para a área de transferência!)"
                    )
                    copy(date)
                    time.sleep(0.5)
                    wait_key_press(self.KEY_NEXT)
                case "próximo":
                    spinner("Continuando")
                case "sair":
                    self.exit_task()
                    spinner()
                    return

        print("[bold green]Não há mais funcionários desligados![/bold green]")
        self.exit_task()
