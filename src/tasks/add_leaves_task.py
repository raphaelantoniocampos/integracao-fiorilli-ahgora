import os
import tempfile
from pathlib import Path

import pandas as pd
from InquirerPy import inquirer
from pyperclip import copy
from rich import print
from rich.table import Table

from src.managers.data_manager import DataManager
from src.managers.file_manager import FileManager
from src.models.key import Key, wait_key_press
from src.models.task import Task
from src.tasks.task_runner import TaskRunner
from src.utils.constants import (
    FIORILLI_DIR,
    LEAVES_COLUMNS,
    UPLOAD_LEAVES_COLUMNS,
)
from src.utils.ui import console, spinner


class AddLeavesTask(TaskRunner):
    KEY_CONTINUE = Key("F2", "green", "continuar")
    KEY_STOP = Key("F4", "red3", "sair")
    KEY_REPEAT = Key("F3", "yellow", "repetir")

    def __init__(self, task: Task):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self.temp_dir_path = Path(tmpdirname)
            super().__init__(task)

    def run(self):
        print(f"\n[bold yellow]{'-' * 15} AFASTAMENTOS! {'-' * 15}[/bold yellow]")

        leaves_bytes = (FIORILLI_DIR / "leaves.csv").read_bytes()

        view_leaves_path = self.temp_dir_path / "leaves.csv"
        upload_leaves_path = self.temp_dir_path / "upload_leaves.csv"
        filter_path = self.temp_dir_path / "filter.txt"
        upload_file_path = self.temp_dir_path / "upload.txt"

        view_leaves_path.write_bytes(leaves_bytes)

        data_manager = DataManager()

        leaves_df = data_manager.read_csv(view_leaves_path, columns=LEAVES_COLUMNS)
        while True:
            self.df_to_upload(leaves_df, upload_leaves_path)
            self.ask_to_insert_file(upload_leaves_path)

            if wait_key_press([self.KEY_CONTINUE, self.KEY_STOP]) == "sair":
                return

            spinner("Aguarde")
            print(
                "\nInsira os erros de registros no arquivo e salve (Ctrl+S) no arquivo [violet]filter.txt[/]"
            )
            filter_path.touch()
            os.startfile(filter_path)

            if wait_key_press([self.KEY_CONTINUE, self.KEY_STOP]) == "sair":
                return

            spinner("Aguarde")

            error_groups = self.process_filter_errors(filter_path)
            self.display_error_groups(error_groups)
            if inquirer.confirm(
                message="Deseja editar algum afastamento?",
                default=False,
            ).execute():
                repeat = True
                while repeat:
                    leaves_df = self.edit_leaves_interactive(leaves_df, filter_path)
                    if leaves_df is not None:
                        self.df_to_upload(leaves_df, upload_leaves_path)
                    if not inquirer.confirm(
                        message="Continuar editando?",
                        default=True,
                    ).execute():
                        repeat = False

            if not inquirer.confirm(
                message="Repetir importação?",
                default=False,
            ).execute():
                break

        filter_numbers = self.read_filter_numbers(filter_path)

        file_size = self.filter_lines(
            upload_leaves_path,
            upload_file_path,
            filter_numbers,
        )

        spinner("Aguarde")
        if file_size == 0:
            print("\nNenhum novo afastamento.")
            self.exit_task()
            return

        self.show_leaves(
            leaves_df.drop(
                [x - 1 for x in filter_numbers],
                axis=0,
            )
        )
        print("Arquivo '[bold green]new_leaves.txt[/bold green]' gerado com sucesso!")

        self.ask_to_insert_file(upload_file_path)
        wait_key_press(self.KEY_CONTINUE)

        spinner("Aguarde")
        self.exit_task()
        return

    def df_to_upload(self, leaves_df: pd.DataFrame, file_path: Path):
        FileManager.save_df(
            df=leaves_df,
            path=file_path,
            header=False,
            columns=UPLOAD_LEAVES_COLUMNS,
        )

    def filter_lines(self, leaves_path, upload_file_path, filter_numbers) -> int:
        with (
            open(leaves_path, "r", encoding="utf-8") as infile,
            open(upload_file_path, "w", encoding="utf-8") as outfile,
        ):
            lines_written = 0
            for index, line in enumerate(infile, start=1):
                if index not in filter_numbers:
                    outfile.write(line)
                    lines_written += 1
            return lines_written

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

    def edit_leaves_interactive(self, df, filter_path):
        """Permite edição interativa dos afastamentos"""
        choices = []
        for i, series in df.iterrows():
            display_text = (
                f"{series['id']} | {series.get('name', 'N/A')} | "
                f"{series['cod']} ({series.get('cod_name', 'N/A')}) | "
                f"{series['duration']} dias | "
                f"{series['start_date']} a {series['end_date']}"
            )
            choices.append((display_text, i + 1))

        selected = inquirer.fuzzy(
            message="Selecione o afastamento para editar:",
            choices=choices,
            mandatory=False,
            border=True,
        ).execute()

        if not selected:
            return df

        selected_idx = int(selected[1] - 1)
        selected_row = df.iloc[selected_idx]

        print("\n[bold]Editando afastamento:[/bold]")
        print(f"ID: {selected_row['id']}")
        print(f"Nome: {selected_row.get('name', 'N/A')}")
        print(f"Código: {selected_row['cod']} ({selected_row.get('cod_name', 'N/A')})")
        print(f"Período: {selected_row['start_date']} a {selected_row['end_date']}")
        print(f"Duração: {selected_row.get('duration', 'N/A')} dias\n")

        edit_options = [
            ("Matrícula", "id"),
            ("Código", "cod"),
            ("Data de Início", "start_date"),
            ("Data de Fim", "end_date"),
            ("Hora de Início", "start_time"),
            ("Hora de Fim", "end_time"),
            ("Cancelar", None),
        ]

        field_to_edit = inquirer.select(
            message="O que deseja editar?",
            choices=[(opt[0], opt[1]) for opt in edit_options],
            default=None,
        ).execute()[1]

        if not field_to_edit:
            return df

        new_value = inquirer.text(
            message=f"Novo valor para {field_to_edit} (atual: {
                selected_row[field_to_edit]
            }):",
            default=str(selected_row[field_to_edit]),
        ).execute()

        df.at[selected_idx, field_to_edit] = new_value

        if field_to_edit in ["start_date", "end_date"]:
            start = pd.to_datetime(df.at[selected_idx, "start_date"])
            end = pd.to_datetime(df.at[selected_idx, "end_date"])
            duration = (end - start).days + 1
            df.at[selected_idx, "duration"] = max(1, duration)

        print("\n[bold green]Afastamento atualizado com sucesso![/bold green]")
        return df

    def show_leaves(self, df):
        """Mostra todos os afastamentos de forma formatada"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Nome")
        table.add_column("Código")
        table.add_column("Tipo")
        table.add_column("Início")
        table.add_column("Fim")
        table.add_column("Duração")

        for _, row in df.iterrows():
            table.add_row(
                str(row["id"]),
                row.get("name", "N/A"),
                str(row["cod"]),
                row.get("cod_name", "N/A"),
                str(row["start_date"]),
                str(row["end_date"]),
                str(row.get("duration", "N/A")),
            )

        print(f"\n[bold]{len(df)} NOVOS AFASTAMENTOS![/bold]\n")

        console.print(table)

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

    def ask_to_insert_file(self, file):
        print(
            f"Insira o arquivo [bold green]{
                str(file)
            }[/bold green] na importação de afastamentos AHGORA."
        )
        print("Selecione [bold white]pw_afimport_01[/bold white].")
        print("Clique em [white on dark_green] Obter Registros[/white on dark_green].")
        copy(str(self.temp_dir_path))
        print(
            f"Caminho '{
                str(self.temp_dir_path)
            }' copiado para a área de transferência!)\n"
        )
