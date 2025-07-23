import time

import keyboard
import pandas as pd
import pyautogui
from InquirerPy import inquirer
from pyperclip import copy
from rich import print

from src.models.key import KEY_NEXT, KEY_STOP, Key, wait_key_press
from src.models.task import Task
from src.tasks.task_runner import TaskRunner
from src.utils.ui import spinner


class ColumnConfig:
    def __init__(self, label: str, color: str, key_char: str):
        self.label = label
        self.style = f"[{color}]"
        self.styled_label = f"[{color}]{self.label}[/]"
        self.key_message = f"escrever o/a {self.label.lower()}"
        self.key = Key(key_char, color, self.key_message)


class UpdateEmployeesTask(TaskRunner):
    COLUMN_CONFIG = {
        "name": ColumnConfig("NOME", "white", "shift+1"),
        "admission_date": ColumnConfig("DATA ADMISSÃO", "green", "shift+2"),
        "dismissal_date": ColumnConfig("DATA DEMISSÃO", "red", "shift+3"),
        "position": ColumnConfig("CARGO", "cyan", "shift+4"),
        "department": ColumnConfig("DEPARTAMENTO", "violet", "shift+5"),
    }

    def __init__(self, task: Task):
        super().__init__(task)

    def run(self):
        df = self.task.data

        for i, series in df.iterrows():
            employee_name = series["name_ahgora"]

            detected_changes = []
            for col_name, config in self.COLUMN_CONFIG.items():
                fiorilli_col = f"{col_name}_fiorilli_norm"
                ahgora_col = f"{col_name}_ahgora_norm"
                if fiorilli_col in series and ahgora_col in series:
                    if series[fiorilli_col] != series[ahgora_col]:
                        detected_changes.append(
                            {
                                "config": config,
                                "name": col_name,
                                "old_value": series[f"{col_name}_ahgora"],
                                "new_value": series[f"{col_name}_fiorilli"],
                            }
                        )

            if not detected_changes:
                continue

            print(
                f"\n[bold gold1]{'-' * 15} FUNCIONÁRIO ALTERADO! {
                    '-' * 15
                }[/bold gold1]"
            )
            # FIX: temp
            # TODO: move this to data manager
            # print(f"{employee_name} - {employee_id}")

            resultados = {}

            # 1. Campos padrões
            for key, value in series.items():
                if not any(
                    suffix in key for suffix in ["_fiorilli", "_ahgora", "_norm"]
                ):
                    resultados[key] = value

            # 2. Comparação de campos *_fiorilli_norm vs *_ahgora_norm
            for col in series.index:
                if col.endswith("_fiorilli_norm"):
                    base = col.replace("_fiorilli_norm", "")
                    col_fiorilli = col
                    col_ahgora = f"{base}_ahgora_norm"

                    if col_ahgora in series:
                        val_fiorilli = series[col_fiorilli]
                        val_ahgora = series[col_ahgora]

                        if (
                            pd.isna(val_fiorilli)
                            or pd.isna(val_ahgora)
                            or val_fiorilli != val_ahgora
                        ):
                            resultados[f"{base}_fiorilli"] = val_fiorilli
                            resultados[f"{base}_ahgora"] = val_ahgora
                        else:
                            resultados[base] = val_fiorilli

            # Criar nova Series com os resultados
            series = pd.Series(resultados)

            # Exibir

            print(series)
            print("\n")

            change_labels = [
                change["config"].styled_label for change in detected_changes
            ]
            print(f"Alterar {' e '.join(change_labels)}")

            for change in detected_changes:
                config = change["config"]
                print(f"Antigo {config.label} (Ahgora): {change['old_value']}")
                print(
                    f"Novo {config.label} (Fiorilli): {config.style}{
                        change['new_value']
                    }[/]"
                )

            print("\n")
            copy(employee_name)
            print(f"(Nome '{employee_name}' copiado para a área de transferência!)")

            while True:
                active_keys = [change["config"].key for change in detected_changes]
                action_map = {
                    change["config"].key_message: change["new_value"]
                    for change in detected_changes
                }

                keys_to_wait = active_keys + [KEY_NEXT, KEY_STOP]

                pressed_action = wait_key_press(keys_to_wait)

                if pressed_action in action_map:
                    value_to_write = str(action_map[pressed_action])
                    copy(value_to_write)
                    keyboard.send("backspace")
                    pyautogui.write(value_to_write, interval=0.02)
                    time.sleep(0.5)
                elif pressed_action == KEY_NEXT.action:
                    spinner("Continuando")
                    break
                elif pressed_action == KEY_STOP.action:
                    self.exit_task()
                    spinner()
                    return

                if not inquirer.confirm(
                    message="Repetir ação?", default=False
                ).execute():
                    break

        print("[bold green]Não há mais funcionários para alterar![/bold green]")
        self.exit_task()
