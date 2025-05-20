import time

from rich.console import Console

console = Console()


def spinner(
    wait_string: str = "Voltando",
    wait_time: float = 0.40,
):
    with console.status(f"[bold green]{wait_string}...[/bold green]", spinner="dots"):
        time.sleep(wait_time)
