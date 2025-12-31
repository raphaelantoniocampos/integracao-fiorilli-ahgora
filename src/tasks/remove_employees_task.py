import time

from pyperclip import copy
from rich import print

from src.models.key import wait_key_press, KEY_CONTINUE, KEY_NEXT, KEY_STOP
from src.models.task import Task
from src.tasks.task_runner import TaskRunner
from src.utils.ui import spinner


class RemoveEmployeesTask(TaskRunner):
    def __init__(self, task: Task):
        super().__init__(task)

    def run(self):
        df = self.task.data
        for i, row in df.iterrows():
            print(
                f"\n[bold gold1]{'-' * 25} FUNCIONÁRIO DESLIGADO! {
                    '-' * 25
                }[/bold gold1]"
            )
            print(row)
            id = row["id"]
            copy(id)
            print("\nProcure o nome e clique no [bold red]x[/bold red]")
            print(f"(Matrícula '{id}' copiado para a área de transferência!)\n")
            match wait_key_press([KEY_CONTINUE, KEY_NEXT, KEY_STOP]):
                case "continuar":
                    spinner("Continuando")
                    date = row["dismissal_date"]
                    print(
                        f"(Data de Desligamento '{
                            date
                        }' copiado para a área de transferência!)"
                    )
                    copy(date)
                    time.sleep(0.5)
                    wait_key_press(KEY_NEXT)
                case "próximo":
                    spinner("Continuando")
                case "sair":
                    self.exit_task()
                    spinner()
                    return

        print("[bold green]Não há mais funcionários desligados![/bold green]")
        self.exit_task()
