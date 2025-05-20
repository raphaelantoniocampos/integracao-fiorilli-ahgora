import os
import tempfile
from pathlib import Path

from InquirerPy import inquirer
from pyperclip import copy
from rich import print

from src.managers.file_manager import FileManager
from src.models.key import Key, wait_key_press
from src.models.task import Task
from src.tasks.task_runner import TaskRunner
from src.utils.constants import DATA_DIR, TASKS_DIR
from src.utils.ui import spinner


class AddAbsencesTask(TaskRunner):
    KEY_CONTINUE = Key("F2", "green", "continuar")
    KEY_STOP = Key("F4", "red3", "sair")
    KEY_REPEAT = Key("F3", "yellow", "repetir")

    def __init__(self, task: Task):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self.temp_dir_path = Path(tmpdirname)
            super().__init__(task)

    def run(self):
        print(f"\n[bold yellow]{'-' * 15} AFASTAMENTOS! {'-' * 15}[/bold yellow]")

        absences_bytes = (FIORILLI_DIR / "absences.csv").read_bytes()

        temp_absences_file = self.temp_dir_path / "absences.csv"
        filter_file = self.temp_dir_path / "filter.txt"
        new_absences_file = self.temp_dir_path / "new_absences.txt"

        temp_absences_file.write_bytes(absences_bytes)

        while True:
            self.ask_to_insert_file("absences.csv")
            if wait_key_press([self.KEY_CONTINUE, self.KEY_STOP]) == "sair":
                return

            spinner("Aguarde", 1)
            print(
                "\nInsira os erros de registros no arquivo e salve (Ctrl+S) no arquivo [violet]filter.txt[/]"
            )
            filter_file.touch()
            os.startfile(filter_file)

            if wait_key_press([self.KEY_CONTINUE, self.KEY_STOP]) == "sair":
                return

            spinner("Aguarde", 1)

            error_groups = self.process_filter_errors(filter_file)
            self.display_error_groups(error_groups)
            if inquirer.confirm(message="Editar arquivo?", default=False).execute():
                os.startfile(temp_absences_file)
            if not inquirer.confirm(message="Repetir", default=False).execute():
                break

        filter_numbers_file = self.read_filter_numbers(filter_file)

        file_size = self.filter_lines(
            temp_absences_file, new_absences_file, filter_numbers_file
        )

        spinner("Aguarde", 1)
        if file_size == 0:
            print("\nNenhum novo afastamento.")
            self.exit_task(temp_absences_file)
            return

        print(f"\n[bold]{file_size} NOVOS AFASTAMENTOS![/bold]\n")
        print("Arquivo '[bold green]new_absences.txt[/bold green]' gerado com sucesso!")

        self.ask_to_insert_file("new_absences.txt")
        wait_key_press(self.KEY_CONTINUE)

        spinner("Aguarde", 1)
        self.exit_task(temp_absences_file)
        return

    def filter_lines(
        self, absences_file, new_absences_file, filter_numbers_file
    ) -> int:
        with (
            open(absences_file, "r", encoding="utf-8") as infile,
            open(new_absences_file, "w", encoding="utf-8") as outfile,
        ):
            lines_written = 0
            for index, line in enumerate(infile, start=1):
                if index not in filter_numbers_file:
                    outfile.write(line)
                    self._get_line_absences_data(line)
                    lines_written += 1
            return lines_written

    def _get_line_absences_data(self, line: str):
        return line

    def process_filter_errors(self, file_path):
        """Processa o arquivo de erros e retorna um dicionário com os erros agrupados"""
        error_groups = {
            "Intersecção com afastamento existente": [],
            "Intersecção com período bloqueado": [],
            "Matrícula inexistente": [],
            "Informe matrícula": [],
            "Outros erros": [],
        }

        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                if "Erro ao obter registros" in line:
                    continue
                elif "Intersecção com afastamento existente" in line:
                    error_groups["Intersecção com afastamento existente"].append(line)
                elif "Intersecção com período bloqueado" in line:
                    error_groups["Intersecção com período bloqueado"].append(line)
                elif "Matrícula" in line and "inexistente" in line:
                    error_groups["Matrícula inexistente"].append(line)
                elif "Informe matrícula" in line:
                    error_groups["Informe matrícula"].append(line)
                else:
                    error_groups["Outros erros"].append(line)

        return error_groups

    def display_error_groups(self, error_groups):
        """Exibe os erros agrupados por categoria"""

        print("\n[bold yellow]RESUMO DE ERROS ENCONTRADOS:[/bold yellow]")

        for error_type, errors in error_groups.items():
            if not errors:
                continue

            print(f"\n[bold]{error_type.upper()}:[/bold] {len(errors)} ocorrências")

            if (
                not error_type == "Intersecção com afastamento existente"
                and not error_type == "Intersecção com período bloqueado"
            ):
                for error in errors:
                    print(f"  - {error}")

    def read_filter_numbers(self, file_path):
        """Lê o arquivo TXT e retorna uma lista com os números dos registros."""
        filter_numbers = []
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                if "registro" in line:
                    start = line.find("[") + 1
                    end = line.find("]")
                    if start > 0 and end > start:
                        try:
                            filter_number = int(line[start:end])
                            filter_numbers.append(filter_number)
                        except ValueError:
                            continue
        return filter_numbers

    def ask_to_insert_file(self, file_name):
        print(
            f"Insira o arquivo [bold green]{file_name}[/bold green] na importação de afastamentos AHGORA."
        )
        print("Selecione [bold white]pw_afimport_01[/bold white].")
        print("Clique em [white on dark_green] Obter Registros[/white on dark_green].")
        copy(str(self.temp_dir_path))
        print(
            f"Caminho '{str(self.temp_dir_path)}' copiado para a área de transferência!)\n"
        )

    def exit_task(self, temp_absences):
        file_manager = FileManager()
        file_manager.move_file(
            source=temp_absences,
            destination=TASKS_DIR / "absences.csv",
        )
        spinner()
