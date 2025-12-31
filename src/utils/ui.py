import time

from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator
from rich.console import Console
from rich.panel import Panel

from src.models.task import Task
from src.utils.constants import INQUIRER_KEYBINDINGS
from src.utils.version import get_project_version

PROJECT_VERSION = get_project_version()

DEFAULT_MESSAGE = "Selecione uma opção"
DEFAULT_INSTRUCTIONS = "Selecione o número ou navegue com as setas do teclado."
DEFAULT_LONG_INSTRUCTIONS = f"""
[Enter] seleciona • [Esc + Esc] cancela [Ctrl+C] sair
{PROJECT_VERSION} • MIT License • © 2025 Raphael Campos
"""

console = Console()


def spinner(
    wait_string: str = "Voltando",
    wait_time: float = 0.15,
):
    with console.status(
        f"[bold green]{wait_string}...[/bold green]",
        spinner="dots",
    ):
        time.sleep(wait_time)


def default_header(name: str):
    console.print(
        Panel.fit(
            name.upper(),
            style="bold cyan",
        )
    )


def menu(
    name: str,
    choices: dict[str, any],
    header=default_header,
    message: str = DEFAULT_MESSAGE,
    go_back_text: str = "Voltar",
):
    header(name)
    if go_back_text:
        choices[go_back_text] = spinner

    choice_name = inquirer.rawlist(
        message=message,
        choices=choices.keys(),
        keybindings=INQUIRER_KEYBINDINGS,
        instruction=DEFAULT_INSTRUCTIONS,
        long_instruction=DEFAULT_LONG_INSTRUCTIONS,
        mandatory=False,
    ).execute()
    if not choice_name:
        choice_name = go_back_text
    return choices.get(choice_name)


def main_header():
    console.print(
        Panel.fit(r"""[bold cyan]
    ______ _       _____                 
    |  ___(_)     |  __ \                
    | |_   _  ___ | |  \/ ___  _ __ __ _ 
    |  _| | |/ _ \| | __ / _ \| '__/ _` |
    | |   | | (_) | |_\ \ (_) | | | (_| |
    \_|   |_|\___/ \____/\___/|_|  \__,_|
                                         
[/bold cyan][gold1]Automação de Sistemas de Ponto Eletrônico e RH[/gold1]
""",
            subtitle="[green]github.com/raphaelantoniocampos/fiogora[/green]",
        )
    )
    console.print()


def main_menu(
    tasks: list[Task],
    choices: dict[str, callable],
):
    console.clear()
    main_header()

    tasks_panel = get_tasks_panel(tasks)
    console.print(tasks_panel)

    return menu(
        name="Main",
        choices=choices,
        header=lambda str: None,
        go_back_text="",
    )


def get_tasks_panel(tasks: list[Task]) -> Panel:
    task_options = [f"[bold cyan]•[/] {task.option}" for task in tasks if task.option]

    if not task_options:
        task_options += ["[green]• Nenhuma tarefa pendente.[/green]"]

        return Panel.fit(
            "[green]• Nenhuma tarefa pendente.[/green]",
            title="[bold]Tarefas Pendentes[/bold]",
            border_style="green",
            padding=(1, 2),
        )

    return Panel.fit(
        "\n".join(task_options),
        title="[bold]Tarefas Pendentes[/bold]",
        border_style="gold1",
        padding=(1, 2),
    )


def get_number(message: str, min: int, max: int):
    return inquirer.number(
        message=message,
        min_allowed=min,
        max_allowed=max,
        validate=EmptyInputValidator(),
    ).execute()
