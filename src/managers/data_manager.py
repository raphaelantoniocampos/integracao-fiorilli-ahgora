import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from InquirerPy import inquirer

from src.managers.file_manager import FileManager
from src.utils.config import Config
from src.utils.constants import (
    AHGORA_DIR,
    AHGORA_EMPLOYEES_COLUMNS,
    COLUMNS_TO_VERIFY_CHANGE,
    DATA_DIR,
    FIORILLI_DIR,
    FIORILLI_EMPLOYEES_COLUMNS,
    INQUIRER_KEYBINDINGS,
    LEAVES_COLUMNS,
    PT_MONTHS,
    TASKS_DIR,
    UPLOAD_LEAVES_COLUMNS,
)
from src.utils.ui import console, menu, spinner


class DataManager:
    def open(self):
        DATA_MENU_CHOICES = {
            "Analisar Dados": self.analyze,
            "Visualizar Dados": self.visualizer,
        }
        return menu(
            name="Dados",
            choices=DATA_MENU_CHOICES,
        )

    def analyze(self):
        try:
            with console.status(
                "[bold green]Analisando dados...[/bold green]", spinner="dots"
            ):
                fiorilli_employees, ahgora_employees = self.get_employees_data()
                last_leaves, all_leaves = self.get_leaves_data()

                leave_codes = self.read_csv(
                    DATA_DIR / "leave_codes.csv", columns=["cod", "desc"]
                )
                all_leaves = self.get_view_leaves(
                    leaves_df=all_leaves,
                    fiorilli_employees=fiorilli_employees,
                    leave_codes=leave_codes,
                )

                (
                    new_employees_df,
                    dismissed_employees_df,
                    changed_employees_df,
                    new_leaves_df,
                ) = self.generate_tasks_dfs(
                    fiorilli_employees=fiorilli_employees,
                    ahgora_employees=ahgora_employees,
                    last_leaves=last_leaves,
                    all_leaves=all_leaves,
                )

                self.save_tasks_dfs(
                    new_employees_df=new_employees_df,
                    dismissed_employees_df=dismissed_employees_df,
                    changed_employees_df=changed_employees_df,
                    new_leaves_df=new_leaves_df,
                )

            Config.update_last_analisys()
            FileManager.setup()
            console.log("[bold green]Dados sincronizados com sucesso![/bold green]\n")
            time.sleep(1)
        except KeyboardInterrupt as e:
            console.log(f"[bold red]Erro ao sincronizar dados: {e}[/bold red]\n")
            time.sleep(1)

        except FileNotFoundError as e:
            config = Config()
            files = config.status.missing_files
            for file in files:
                console.log(Path(file).name)
            console.log(f"[bold red]Erro ao sincronizar dados: {e}[/bold red]\n")
            time.sleep(1)
            inquirer.confirm(
                message=f"{len(files)} arquivos necessários.\nContinuar",
                default=True,
            ).execute()

    def visualizer(self):
        ahgora_files = [file for file in AHGORA_DIR.iterdir()]
        fiorilli_files = [file for file in FIORILLI_DIR.iterdir()]
        tasks_file = [file for file in TASKS_DIR.iterdir()]
        files = {
            str(file.parent).split("\\")[-1] + "\\" + str(file.name): file
            for file in ahgora_files + fiorilli_files + tasks_file
        }
        files["Voltar"] = None
        while True:
            # TODO: update menu
            option = inquirer.select(
                message="Selecione um arquivo",
                choices=[
                    f"{i + 1}) {item[0]}"
                    for i, item in enumerate(
                        files.items(),
                    )
                ],
                mandatory=False,
                keybindings=INQUIRER_KEYBINDINGS,
            ).execute()
            if not option:
                continue

            if "Voltar" in option:
                spinner()
                return

            try:
                df = self.read_csv(files[option[3:].strip()])
            except pd.errors.EmptyDataError:
                console.log("Vazio.")
                continue

            if df.empty:
                console.log("Vazio.")
                continue

            columns = df.columns.to_list()

            choices = []
            for i, row in df.iterrows():
                choices.append(
                    row.to_list(),
                )

            inquirer.fuzzy(
                message=option,
                choices=choices,
                keybindings=INQUIRER_KEYBINDINGS,
                instruction=columns,
                mandatory=False,
                border=True,
            ).execute()

    def get_view_leaves(
        self,
        leaves_df: pd.DataFrame,
        fiorilli_employees: pd.DataFrame,
        leave_codes: pd.DataFrame,
    ) -> pd.DataFrame:
        leaves_df["start_date"] = pd.to_datetime(
            leaves_df["start_date"],
            format="%d/%m/%Y",
        )
        leaves_df["end_date"] = pd.to_datetime(
            leaves_df["end_date"],
            format="%d/%m/%Y",
        )

        leaves_df = leaves_df.merge(
            fiorilli_employees[["id", "name"]], on="id", how="left"
        )

        leaves_df = leaves_df.merge(
            leave_codes[["cod", "desc"]], on="cod", how="left"
        ).rename(columns={"desc": "cod_name"})

        leaves_df["duration"] = (
            leaves_df["end_date"] - leaves_df["start_date"]
        ).dt.days + 1
        leaves_df["duration"] = leaves_df["duration"].clip(lower=1)

        leaves_df = leaves_df[LEAVES_COLUMNS]

        self.update_leaves_dfs(
            all_leaves=leaves_df,
        )
        all_leaves_path = FIORILLI_DIR / "leaves.csv"
        all_leaves = self.read_csv(all_leaves_path)

        return all_leaves

    @staticmethod
    def filter_df(df: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
        return df[df["id"].isin(ids)]

    def read_csv(
        self,
        path: Path,
        sep: str = ",",
        encoding: str = "utf-8",
        header: str | None = "infer",
        columns: list[str] = [],
    ) -> pd.DataFrame:
        match path.name:
            case "raw_employees.txt":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        sep="|",
                        encoding="latin1",
                        index_col=False,
                        header=None,
                    ),
                    columns=FIORILLI_EMPLOYEES_COLUMNS,
                )

            case "raw_employees.csv":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=AHGORA_EMPLOYEES_COLUMNS,
                )

            case "ahgora_employees.csv":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                    ),
                    columns=AHGORA_EMPLOYEES_COLUMNS,
                )

            case "fiorilli_employees.csv":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                    ),
                    columns=FIORILLI_EMPLOYEES_COLUMNS,
                )

            case "leaves.csv":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=LEAVES_COLUMNS,
                )
            case "raw_vacations.txt":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=UPLOAD_LEAVES_COLUMNS,
                )

            case "raw_leaves.txt":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=UPLOAD_LEAVES_COLUMNS,
                )
            case _:
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        sep=sep,
                        encoding=encoding,
                        index_col=False,
                        header=header,
                    ),
                    columns=columns,
                )

    def prepare_dataframe(
        self,
        df: pd.DataFrame,
        columns: list[str] = [],
    ) -> pd.DataFrame:
        if columns:
            df.columns = columns
        else:
            columns = df.columns

        for col in df.columns:
            if "date" in col:
                df[col] = df[col].apply(self.convert_date)
                df[col] = pd.to_datetime(
                    df[col],
                    dayfirst=True,
                    format="%d/%m/%Y",
                    errors="coerce",
                )
                df[col] = df[col].dt.strftime("%d/%m/%Y")

        if "cpf" in df.columns:
            df["cpf"] = df["cpf"].fillna("").astype(str).str.zfill(11)

        if "cod" in df.columns:
            df["cod"] = df["cod"].fillna("").astype(str).str.zfill(3)

        if "name" in df.columns:
            df["name"] = df["name"].str.strip().str.upper()

        if "pis_pasep" in df.columns:
            if not pd.api.types.is_string_dtype(df["pis_pasep"]):
                df["pis_pasep"] = df["pis_pasep"].fillna(0).astype(int).astype(str)

        if "id" in df.columns:
            df["id"] = df["id"].astype(str).str.zfill(6)

        if "desc" in df.columns:
            df["desc"] = df["desc"].astype(str)

        return df

    def convert_date(self, date_str: str):
        not_a_date = (
            pd.isna(date_str) or not isinstance(date_str, str) or date_str == " "
        )

        if not_a_date:
            return pd.NaT

        partes = date_str.split(", ")
        if len(partes) > 1:
            date_str = partes[1]
        for pt, en in PT_MONTHS.items():
            date_str = date_str.replace(f"{pt}/", f"{en}/")
        try:
            return pd.to_datetime(
                date_str,
                format="%d/%b/%Y",
                errors="raise",
            )
        except ValueError:
            try:
                return pd.to_datetime(
                    date_str,
                    format="%d/%m/%Y",
                    errors="raise",
                )
            except ValueError:
                try:
                    return pd.to_datetime(
                        date_str,
                        format="%d/%b/%Y %H:%M",
                        errors="raise",
                    )
                except ValueError:
                    return pd.to_datetime(
                        date_str,
                        format="ISO8601",
                        errors="coerce",
                    )

    def generate_tasks_dfs(
        self,
        fiorilli_employees: pd.DataFrame,
        ahgora_employees: pd.DataFrame,
        last_leaves: pd.DataFrame,
        all_leaves: pd.DataFrame,
    ) -> None:
        """
        returns
            new_employees_df,
            dismissed_employees_df,
            changed_employees_df,
            new_leaves_df,
        """
        console.log("Gerando tabelas de tarefas")
        time.sleep(0.5)
        fiorilli_dismissed_df = fiorilli_employees[
            fiorilli_employees["dismissal_date"].notna()
        ]
        fiorilli_dismissed_ids = set(fiorilli_dismissed_df["id"])
        ahgora_dismissed_df = ahgora_employees[
            ahgora_employees["dismissal_date"].notna()
        ]
        ahgora_dismissed_ids = set(ahgora_dismissed_df["id"])
        dismissed_ids = ahgora_dismissed_ids | fiorilli_dismissed_ids

        fiorilli_active_employees = fiorilli_employees[
            ~fiorilli_employees["id"].isin(dismissed_ids)
        ]

        new_employees_df = self._get_new_employees_df(
            fiorilli_active_employees=fiorilli_active_employees,
            ahgora_employees=ahgora_employees,
            dismissed_ids=dismissed_ids,
        )

        dismissed_employees_df = self._get_dismissed_employees_df(
            ahgora_employees=ahgora_employees,
            fiorilli_dismissed_df=fiorilli_dismissed_df,
            fiorilli_dismissed_ids=fiorilli_dismissed_ids,
            ahgora_dismissed_ids=ahgora_dismissed_ids,
        )
        changed_employees_df = self._get_changed_employees_df(
            fiorilli_active_employees=fiorilli_active_employees,
            ahgora_employees=ahgora_employees,
        )
        new_leaves_df = self._get_new_leaves_df(
            last_leaves=last_leaves,
            all_leaves=all_leaves,
        )

        return (
            new_employees_df,
            dismissed_employees_df,
            changed_employees_df,
            new_leaves_df,
        )

    def _get_new_employees_df(
        self,
        fiorilli_active_employees: pd.DataFrame,
        ahgora_employees: pd.DataFrame,
        dismissed_ids: set[int],
    ) -> pd.DataFrame:
        console.log("Buscando novos funcionários")
        time.sleep(0.5)
        ahgora_ids = set(ahgora_employees["id"])

        new_employees_df = fiorilli_active_employees[
            ~fiorilli_active_employees["id"].isin(ahgora_ids)
        ]

        new_employees_df = new_employees_df[
            new_employees_df["binding"] != "AUXILIO RECLUSAO"
        ]

        console.log(
            f"{len(new_employees_df)} novos funcionários",
        )
        time.sleep(0.5)
        return new_employees_df

    def _get_dismissed_employees_df(
        self,
        ahgora_employees: pd.DataFrame,
        fiorilli_dismissed_df: pd.DataFrame,
        fiorilli_dismissed_ids: set[int],
        ahgora_dismissed_ids: set[int],
    ) -> pd.DataFrame:
        console.log("Buscando funcionários desligados")
        time.sleep(0.5)
        dismissed_employees_df = ahgora_employees[
            ahgora_employees["id"].isin(fiorilli_dismissed_ids)
            & ~ahgora_employees["id"].isin(ahgora_dismissed_ids)
        ]

        dismissed_employees_df = dismissed_employees_df.drop(columns=["dismissal_date"])
        dismissed_employees_df = dismissed_employees_df.merge(
            fiorilli_dismissed_df[["id", "dismissal_date"]],
            on="id",
            how="left",
        )
        dismissed_employees_df["dismissal_date"] = pd.to_datetime(
            dismissed_employees_df["dismissal_date"],
            format="%d/%m/%Y",
        )

        today = datetime.today()
        dismissed_employees_df = dismissed_employees_df[
            dismissed_employees_df["dismissal_date"] <= today
        ]

        console.log(
            f"{len(dismissed_employees_df)} funcionários desligados",
        )
        time.sleep(0.5)

        return dismissed_employees_df

    def _get_changed_employees_df(
        self,
        fiorilli_active_employees: pd.DataFrame,
        ahgora_employees: pd.DataFrame,
    ) -> pd.DataFrame:
        console.log("Buscando funcionários atualizados")
        time.sleep(0.5)
        merged_employees = fiorilli_active_employees.merge(
            ahgora_employees,
            on="id",
            suffixes=("_fiorilli", "_ahgora"),
            how="inner",
        )

        for col in COLUMNS_TO_VERIFY_CHANGE:
            if f"{col}_fiorilli" in merged_employees:
                merged_employees[f"{col}_fiorilli_norm"] = merged_employees[
                    f"{col}_fiorilli"
                ].apply(self.normalize_text)

            if f"{col}_ahgora" in merged_employees:
                merged_employees[f"{col}_ahgora_norm"] = merged_employees[
                    f"{col}_ahgora"
                ].apply(self.normalize_text)

        change_conditions = []
        placeholder = "___VALOR_NULO_TEMPORARIO___"

        for col in COLUMNS_TO_VERIFY_CHANGE:
            fiorilli_norm_col = f"{col}_fiorilli_norm"
            ahgora_norm_col = f"{col}_ahgora_norm"

            if (
                fiorilli_norm_col in merged_employees
                and ahgora_norm_col in merged_employees
            ):
                row_fiorilli = merged_employees[fiorilli_norm_col]
                row_ahgora = merged_employees[ahgora_norm_col]

                condition = row_fiorilli.fillna(placeholder) != row_ahgora.fillna(
                    placeholder
                )
                change_conditions.append(condition)

        if change_conditions:
            combined_condition = change_conditions[0]
            for cond in change_conditions[1:]:
                combined_condition |= cond
        else:
            return pd.DataFrame()

        changed_employees_df = merged_employees[combined_condition]

        console.log(
            f"{len(changed_employees_df)} funcionários atualizados",
        )
        time.sleep(0.5)
        return changed_employees_df

    def _get_new_leaves_df(
        self,
        last_leaves: pd.DataFrame,
        all_leaves: pd.DataFrame,
    ) -> pd.DataFrame:
        console.log("Buscando afastamentos")
        time.sleep(0.5)
        for df in [last_leaves, all_leaves]:
            for col in ["start_date", "end_date"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(
                        df[col],
                        format="%d/%m/%Y",
                    )

        merged = pd.merge(
            last_leaves,
            all_leaves,
            how="outer",
            indicator=True,
        )
        leaves_df = merged[merged["_merge"] == "right_only"].drop(
            "_merge",
            axis=1,
        )

        try:
            not_done_task = self.read_csv(TASKS_DIR / "add_leaves.csv")
        except FileNotFoundError:
            not_done_task = pd.DataFrame()

        if leaves_df.empty and not not_done_task.empty:
            leaves_df = not_done_task

        console.log(f"{len(leaves_df)} novos afastamentos")
        time.sleep(0.5)
        return leaves_df

    def normalize_text(self, text):
        if pd.isna(text):
            return np.nan
        text = str(" ".join(re.split(r"\s+", text, flags=re.UNICODE)))
        normalized = (
            unicodedata.normalize("NFKD", text)
            .encode("ASCII", "ignore")
            .decode("ASCII")
        )
        normalized = self.treat_exceptions_and_typos(normalized)
        return normalized.lower().strip()

    def update_employees_dfs(
        self,
        fiorilli_employees: pd.DataFrame,
        ahgora_employees: pd.DataFrame,
    ):
        console.log("Salvando dados de funcionários")
        time.sleep(0.5)

        FileManager.save_df(
            df=fiorilli_employees,
            path=FIORILLI_DIR / "fiorilli_employees.csv",
        )

        FileManager.save_df(
            df=ahgora_employees,
            path=AHGORA_DIR / "ahgora_employees.csv",
        )

    def update_leaves_dfs(
        self,
        all_leaves: pd.DataFrame,
    ):
        console.log("Salvando dados de afastamentos")
        time.sleep(0.5)

        FileManager.save_df(
            df=all_leaves,
            path=FIORILLI_DIR / "leaves.csv",
            header=False,
        )

    def save_tasks_dfs(
        self,
        new_employees_df: pd.DataFrame,
        dismissed_employees_df: pd.DataFrame,
        changed_employees_df: pd.DataFrame,
        new_leaves_df: pd.DataFrame | None,
    ):
        FileManager.save_df(
            df=new_employees_df,
            path=TASKS_DIR / "add_employees.csv",
        )

        FileManager.save_df(
            df=dismissed_employees_df,
            path=TASKS_DIR / "remove_employees.csv",
        )

        FileManager.save_df(
            df=changed_employees_df,
            path=TASKS_DIR / "update_employees.csv",
        )

        FileManager.save_df(
            df=new_leaves_df,
            path=TASKS_DIR / "add_leaves.csv",
        )

    def get_employees_data(self) -> (pd.DataFrame, pd.DataFrame):
        """
        returns
        fiorilli_employees,
        ahgora_employees
        """
        console.log("Recuperando dados de funcionários")
        time.sleep(0.5)
        raw_fiorilli_employees_path = FIORILLI_DIR / "raw_employees.txt"
        raw_ahgora_employees_path = AHGORA_DIR / "raw_employees.csv"

        raw_fiorilli_employees = self.read_csv(raw_fiorilli_employees_path)
        raw_ahgora_employees = self.read_csv(raw_ahgora_employees_path)

        self.update_employees_dfs(
            fiorilli_employees=raw_fiorilli_employees,
            ahgora_employees=raw_ahgora_employees,
        )

        fiorilli_employees = self.read_csv(
            FIORILLI_DIR / "fiorilli_employees.csv",
        )
        ahgora_employees = self.read_csv(
            AHGORA_DIR / "ahgora_employees.csv",
        )

        return fiorilli_employees, ahgora_employees

    def get_leaves_data(self) -> (pd.DataFrame, pd.DataFrame):
        console.log("Recuperando dados de afastamentos")
        time.sleep(0.5)
        last_leaves_path = FIORILLI_DIR / "leaves.csv"
        raw_leaves_path = FIORILLI_DIR / "raw_leaves.txt"
        raw_vacations_path = FIORILLI_DIR / "raw_vacations.txt"

        match last_leaves_path.exists():
            case True:
                last_leaves = self.read_csv(last_leaves_path)
            case False:
                last_leaves = pd.DataFrame()

        all_leaves = pd.concat(
            [
                self.read_csv(raw_vacations_path),
                self.read_csv(raw_leaves_path),
            ]
        )
        return last_leaves, all_leaves

        # except EmptyDataError:
        #     return last_leaves, pd.DataFrame(columns=LEAVES_COLUMNS)
        # except FileNotFoundError:
        #     return pd.DataFrame(columns=LEAVES_COLUMNS), all_leaves

    def treat_exceptions_and_typos(self, text: str) -> str:
        if text == "VIGILACIA EM SAUDE":
            return "VIGILANCIA EM SAUDE"
        if text == "UBS SAO JOSE/CIDADE JARDIM":
            return "UBS CIDADE JARDIM"
        if text == "FINANCAS":
            return "SECRETARIA MUN. FINANCAS"
        return text
