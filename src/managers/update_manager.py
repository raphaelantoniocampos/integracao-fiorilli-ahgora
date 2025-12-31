
import subprocess
import sys
import tomllib
import urllib.request
import webbrowser
from pathlib import Path
from packaging import version

from rich import print
from rich.panel import Panel
from rich.prompt import Confirm

from src.utils.version import get_project_version


class UpdateManager:
    GITHUB_USER = "raphaelantoniocampos"
    GITHUB_REPO = "fiogora"
    GITHUB_BRANCH = "main"
    RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/pyproject.toml"
    RELEASES_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases"

    @staticmethod
    def get_remote_version() -> str | None:
        """Fetches the project version from the remote repository."""
        try:
            with urllib.request.urlopen(UpdateManager.RAW_URL, timeout=5) as response:
                if response.status == 200:
                    data = tomllib.load(response)
                    return data["project"].get("version")
        except Exception:
            return None
        return None

    @staticmethod
    def is_source_installation() -> bool:
        """Checks if the project is running from source and has git access."""
        is_frozen = getattr(sys, "frozen", False)
        has_git = (Path(".git").exists() or Path("../.git").exists())
        return not is_frozen and has_git

    @staticmethod
    def is_frozen_with_makefile() -> bool:
        """Checks if running as executable but with source/Makefile available nearby."""
        is_frozen = getattr(sys, "frozen", False)
        # Assuming the executable is in dist/AppName/
        # and Makefile is in the project root (2 levels up)
        if not is_frozen:
            return False
        
        exe_dir = Path(sys.executable).parent
        project_root = exe_dir.parents[1]  # dist/AppName -> dist -> root
        makefile = project_root / "Makefile"
        return makefile.exists()

    @staticmethod
    def check_for_updates():
        """Checks for updates and prompts the user if available."""
        print("[dim]Verificando atualizações...[/dim]")
        
        current_version_str = get_project_version()
        remote_version_str = UpdateManager.get_remote_version()

        if not remote_version_str:
            print("[yellow]Não foi possível verificar atualizações.[/yellow]")
            return

        try:
            current = version.parse(current_version_str)
            remote = version.parse(remote_version_str)
        except Exception:
             print("[yellow]Erro ao comparar versões.[/yellow]")
             return

        if remote > current:
            UpdateManager.ask_for_update(str(current), str(remote))

    @staticmethod
    def ask_for_update(current: str, remote: str):
        panel = Panel.fit(
            f"[bold yellow]Nova atualização disponível![/bold yellow]\n\n"
            f"Atual: [red]{current}[/red]  ->  Nova: [green]{remote}[/green]\n",
            title="Update Manager",
            border_style="green",
        )
        print(panel)

        if Confirm.ask("Deseja atualizar agora?", default=True):
            UpdateManager.update()

    @staticmethod
    def update():
        if UpdateManager.is_source_installation():
            UpdateManager.update_via_git()
        elif UpdateManager.is_frozen_with_makefile():
            UpdateManager.update_via_make()
        else:
            UpdateManager.update_manual()

    @staticmethod
    def update_via_git():
        print("[cyan]Executando git pull...[/cyan]")
        try:
            subprocess.run(["git", "pull"], check=True)
            print("[bold green]Atualizado com sucesso! Reinicie a aplicação.[/bold green]")
            sys.exit(0)
        except subprocess.CalledProcessError:
            print("[bold red]Falha ao atualizar via git. Tente manualmente.[/bold red]")

    @staticmethod
    def update_via_make():
        print("[cyan]Código fonte detectado. Reconstruindo executável...[/cyan]")
        try:
            # Determine project root from executable location
            exe_dir = Path(sys.executable).parent
            project_root = exe_dir.parents[1]
            
            subprocess.run(["make", "update"], cwd=project_root, check=True)
            print("[bold green]Executável reconstruído! Reinicie a aplicação.[/bold green]")
            sys.exit(0)
        except subprocess.CalledProcessError:
            print("[bold red]Falha ao executar make update.[/bold red]")

    @staticmethod
    def update_manual():
        print("[yellow]Não foi possível atualizar automaticamente.[/yellow]")
        print(f"Por favor, baixe a nova versão em: {UpdateManager.RELEASES_URL}")
        if Confirm.ask("Abrir link no navegador?", default=True):
             webbrowser.open(UpdateManager.RELEASES_URL)
