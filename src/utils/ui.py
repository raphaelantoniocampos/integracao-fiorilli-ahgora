import time

from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel

from src.models.task import Task
from src.utils.constants import (
    INQUIRER_KEYBINDINGS,
    MAIN_MENU_OPTIONS,
)

console = Console()


def spinner(
    wait_string: str = "Voltando",
    wait_time: float = 0.40,
):
    with console.status(
        f"[bold green]{wait_string}...[/bold green]",
        spinner="dots",
    ):
        time.sleep(wait_time)


def menu_table(tasks: list[Task]):
    console.print(
        Panel.fit(
            "[bold magenta]Integração Fiorilli Ahgora[/bold magenta] - [gold1]Automação de Sistemas de Ponto Eletrônico e RH[/gold1]",
            subtitle="[green]github.com/raphaelantoniocampos/integracao_fiorilli_ahgora[/green]",
        )
    )

    console.print()

    tasks_panel = get_tasks_panel(tasks)
    console.print(tasks_panel)

    answers = inquirer.rawlist(
        message="Selecione uma opção",
        choices=MAIN_MENU_OPTIONS,
        keybindings=INQUIRER_KEYBINDINGS,
        instruction="Selecione o número ou navegue com as setas do teclado.",
        long_instruction="[Enter] confirma • [Espaço] seleciona • [Esc] cancela [Ctrl+C] sair\nMIT License • © 2025 Raphael Campos",
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
