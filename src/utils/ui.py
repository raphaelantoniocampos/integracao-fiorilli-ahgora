import time
from datetime import datetime

from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.models.task import Task
from src.utils.constants import (
    INQUIRER_KEYBINDINGS,
    MAIN_MENU_OPTIONS,
    PT_MONTHS,
    PT_WEEKDAYS,
)

console = Console()


class Header:
    """Display header with clock."""

    def __rich__(self) -> Panel:
        now = datetime.now()

        en_weekday = now.strftime("%a")
        en_month = now.strftime("%b")
        day = now.strftime("%d")
        year = now.strftime("%Y")

        pt_weekday = PT_WEEKDAYS.get(en_weekday, en_weekday)
        pt_month = PT_MONTHS.get(en_month, en_month)

        time_str = now.strftime("%H[blink]:[/]%M[blink]")

        grid = Table.grid()
        grid.add_row(
            f"{pt_weekday} {day} {pt_month} {year}",
        )

        grid.add_row(
            "[b]Integração[/b] Fiorilli/Ahgora",
        )

        grid.add_row(
            time_str,
        )
        return Panel.fit(
            grid,
            style="cyan",
        )


def spinner(
    wait_string: str = "Voltando",
    wait_time: float = 0.40,
):
    with console.status(f"[bold green]{wait_string}...[/bold green]", spinner="dots"):
        time.sleep(wait_time)


def menu_table(tasks: list[Task]):
    header = Header()
    console.print(header)

    tasks_panel = get_tasks_panel(tasks)
    console.print(tasks_panel)

    answers = inquirer.rawlist(
        message="Selecione uma opção",
        choices=MAIN_MENU_OPTIONS,
        keybindings=INQUIRER_KEYBINDINGS,
    ).execute()
    return answers


def get_tasks_panel(tasks: list[Task]) -> Panel:
    task_options = [f"[bold cyan]•[/] {task.option}" for task in tasks if task.option]

    if not task_options:
        task_options.append("[green]• Nenhuma tarefa pendente.[/green]")

        return Panel.fit(
            "[green]• Nenhuma tarefa pendente.[/green]",
            title="[bold]Tarefas Pendentes[/bold]",
            border_style="green",
            padding=(1, 2),
        )

    return Panel.fit(
        "\n".join(task_options),
        title="[bold]Tarefas Pendentes[/bold]",
        border_style="yellow",
        padding=(1, 2),
    )
