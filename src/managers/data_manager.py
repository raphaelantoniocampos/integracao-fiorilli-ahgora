import unicodedata
from datetime import datetime
from pathlib import Path
from time import sleep

import pandas as pd
from InquirerPy import inquirer
from pandas.errors import EmptyDataError
from rich.panel import Panel

from src.managers.file_manager import FileManager as file_manager
from src.utils.config import Config
from src.utils.constants import (
    ABSENCES_COLUMNS,
    AHGORA_DIR,
    DATA_DIR,
    FIORILLI_DIR,
    INQUIRER_KEYBINDINGS,
    PT_MONTHS,
    RAW_AHGORA_EMPLOYEES_COLUMNS,
    RAW_FIORILLI_EMPLOYEES_COLUMNS,
    TASKS_DIR,
    UPLOAD_ABSENCES_COLUMNS,
)
from src.utils.ui import console, spinner


class DataManager:
    def menu(self, name):
        console.print(
            Panel.fit(
                name.upper(),
                style="bold cyan",
            )
        )
        choices = ["Visualizar Dados", "Analisar Dados"]
        choices.append("Voltar")

        option = inquirer.rawlist(
            message="Selecione uma opção",
            choices=choices,
            keybindings=INQUIRER_KEYBINDINGS,
        ).execute()

        if "Visualizar" in option:
            self.visualizer()

        if "Analisar" in option:
            self.analyze()

        if "Voltar" in option:
            spinner()
            return

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

            df = self.read_csv(files[option[3:].strip()])
            if df.empty:
                console.print("Vazio.")
                continue

            columns = df.columns.to_list()

            choices = []
            for i, series in df.iterrows():
                choices.append(
                    series.to_list(),
                )

            inquirer.fuzzy(
                message=option,
                choices=choices,
                keybindings=INQUIRER_KEYBINDINGS,
                instruction=columns,
                mandatory=False,
                border=True,
            ).execute()

    def analyze(self):
        try:
            with console.status(
                "[bold green]Analisando dados...[/bold green]", spinner="dots"
            ):
                ahgora_employees, fiorilli_employees = self.get_employees_data()
                last_absences, all_absences = self.get_absences_data()

                absence_codes = self.read_csv(
                    DATA_DIR / "absence_codes.csv", columns=["cod", "desc"]
                )
                all_absences = self.get_view_absences(
                    all_absences,
                    fiorilli_employees,
                    absence_codes=absence_codes,
                )

                file_manager.save_df(
                    df=ahgora_employees,
                    path=AHGORA_DIR / "employees.csv",
                )
                file_manager.save_df(
                    df=fiorilli_employees,
                    path=FIORILLI_DIR / "employees.csv",
                )

                file_manager.save_df(
                    df=all_absences,
                    path=FIORILLI_DIR / "absences.csv",
                    header=False,
                )

                self.generate_tasks_dfs(
                    fiorilli_employees=fiorilli_employees,
                    ahgora_employees=ahgora_employees,
                    last_absences=last_absences,
                    all_absences=all_absences,
                )

            Config.update_last_analisys()
            console.print("[bold green]Dados sincronizados com sucesso![/bold green]\n")
            sleep(1)
        except KeyboardInterrupt as e:
            console.print(f"[bold red]Erro ao sincronizar dados: {e}[/bold red]\n")
            sleep(1)

        except FileNotFoundError as e:
            console.print(
                f"[bold red]Erro ao analisar dados: {
                    e
                }[/bold red]\nFaça o download primeiro."
            )
            console.print("Pressione [green]qualquer tecla[/] para continuar...")
            input()

    def get_view_absences(
        self,
        absences_df: pd.DataFrame,
        fiorilli_employees: pd.DataFrame,
        absence_codes: pd.DataFrame,
    ) -> pd.DataFrame:
        absences_df["start_date"] = pd.to_datetime(
            absences_df["start_date"],
            format="%d/%m/%Y",
        )
        absences_df["end_date"] = pd.to_datetime(
            absences_df["end_date"],
            format="%d/%m/%Y",
        )

        absences_df = absences_df.merge(
            fiorilli_employees[["id", "name"]], on="id", how="left"
        )

        absences_df = absences_df.merge(
            absence_codes[["cod", "desc"]], on="cod", how="left"
        ).rename(columns={"desc": "cod_name"})

        absences_df["duration"] = (
            absences_df["end_date"] - absences_df["start_date"]
        ).dt.days + 1
        absences_df["duration"] = absences_df["duration"].clip(lower=1)

        absences_df = absences_df[ABSENCES_COLUMNS]
        return absences_df

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
    ):
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
                    columns=RAW_FIORILLI_EMPLOYEES_COLUMNS,
                )

            case "raw_employees.csv":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=RAW_AHGORA_EMPLOYEES_COLUMNS,
                )

            case "add_absences.csv":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=UPLOAD_ABSENCES_COLUMNS,
                )

            case "absences.csv":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=ABSENCES_COLUMNS,
                )
            case "raw_vacations.txt":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=UPLOAD_ABSENCES_COLUMNS,
                )

            case "raw_absences.txt":
                return self.prepare_dataframe(
                    df=pd.read_csv(
                        path,
                        index_col=False,
                        header=None,
                    ),
                    columns=UPLOAD_ABSENCES_COLUMNS,
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
        df,
        columns: list[str] = [],
    ):
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
        last_absences: pd.DataFrame,
        all_absences: pd.DataFrame,
    ) -> None:
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
        new_absences_df = self._get_new_absences_df(
            last_absences=last_absences,
            all_absences=all_absences,
        )

        self.save_tasks_dfs(
            new_employees_df=new_employees_df,
            dismissed_employees_df=dismissed_employees_df,
            changed_employees_df=changed_employees_df,
            new_absences_df=new_absences_df,
        )

    def _get_new_employees_df(
        self,
        fiorilli_active_employees: pd.DataFrame,
        ahgora_employees: pd.DataFrame,
        dismissed_ids: set[int],
    ) -> pd.DataFrame:
        ahgora_ids = set(ahgora_employees["id"])

        new_employees_df = fiorilli_active_employees[
            ~fiorilli_active_employees["id"].isin(ahgora_ids)
        ]

        new_employees_df = new_employees_df[
            new_employees_df["binding"] != "AUXILIO RECLUSAO"
        ]

        return new_employees_df

    def _get_dismissed_employees_df(
        self,
        ahgora_employees: pd.DataFrame,
        fiorilli_dismissed_df: pd.DataFrame,
        fiorilli_dismissed_ids: set[int],
        ahgora_dismissed_ids: set[int],
    ) -> pd.DataFrame:
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

        return dismissed_employees_df

    def _get_changed_employees_df(
        self,
        fiorilli_active_employees: pd.DataFrame,
        ahgora_employees: pd.DataFrame,
    ) -> pd.DataFrame:
        merged_employees = fiorilli_active_employees.merge(
            ahgora_employees, on="id", suffixes=("_fiorilli", "_ahgora"), how="inner"
        )
        change_conditions = []
        columns_to_check = [
            "name",
            "admission_date",
            "dismissal_date",
            "position",
            "department",
        ]
        for col in columns_to_check:
            merged_employees[f"{col}_fiorilli_norm"] = merged_employees[
                f"{col}_fiorilli"
            ].apply(self.normalize_text)
            merged_employees[f"{col}_ahgora_norm"] = merged_employees[
                f"{col}_ahgora"
            ].apply(self.normalize_text)

        condition = (
            merged_employees[f"{col}_fiorilli_norm"]
            != merged_employees[f"{col}_ahgora_norm"]
        )
        change_conditions.append(condition)

        if change_conditions:
            combined_condition = change_conditions[0]
            for cond in change_conditions[1:]:
                combined_condition |= cond
        else:
            return pd.DataFrame()

        changed_employees_df = merged_employees[combined_condition]

        return changed_employees_df

        # position_changed = (
        #     merged_employees["position_fiorilli_norm"]
        #     != merged_employees["position_ahgora_norm"]
        # )
        # location_changed = (
        #     merged_employees["department_fiorilli_norm"]
        #     != merged_employees["department_ahgora_norm"]
        # )

        # changed_employees_df = merged_employees[position_changed | location_changed]
        #
        # return changed_employees_df

    def _get_new_absences_df(
        self,
        last_absences: pd.DataFrame,
        all_absences: pd.DataFrame,
    ) -> pd.DataFrame:
        try:
            for df in [last_absences, all_absences]:
                for col in ["start_date", "end_date"]:
                    if col in df.columns:
                        df[col] = pd.to_datetime(
                            df[col],
                            format="%d/%m/%Y",
                        )

            merged = pd.merge(last_absences, all_absences, how="outer", indicator=True)
            new_absences = merged[merged["_merge"] == "right_only"].drop(
                "_merge", axis=1
            )
            return new_absences

        except TypeError:
            return all_absences

    def normalize_text(self, text):
        if pd.isna(text):
            return ""
        text = str(text)
        normalized = (
            unicodedata.normalize("NFKD", text)
            .encode("ASCII", "ignore")
            .decode("ASCII")
        )
        normalized = self.treat_exceptions_and_typos(normalized)
        return normalized.lower().strip()

    def save_tasks_dfs(
        self,
        new_employees_df,
        dismissed_employees_df,
        changed_employees_df,
        new_absences_df,
    ):
        file_manager.save_df(
            df=new_employees_df,
            path=TASKS_DIR / "add_employees.csv",
        )
        file_manager.save_df(
            df=dismissed_employees_df,
            path=TASKS_DIR / "remove_employees.csv",
        )
        file_manager.save_df(
            df=changed_employees_df,
            path=TASKS_DIR / "update_employees.csv",
        )
        file_manager.save_df(
            df=new_absences_df,
            path=TASKS_DIR / "add_abcenses.csv",
        )

    def get_employees_data(self) -> (pd.DataFrame, pd.DataFrame):
        raw_fiorilli_employees = FIORILLI_DIR / "raw_employees.txt"
        raw_ahgora_employees = AHGORA_DIR / "raw_employees.csv"

        fiorilli_employees = self.read_csv(raw_fiorilli_employees)

        ahgora_employees = self.read_csv(raw_ahgora_employees)
        return ahgora_employees, fiorilli_employees

    def get_absences_data(self) -> pd.DataFrame:
        last_absences_path = TASKS_DIR / "add_absences.csv"
        raw_absences_path = FIORILLI_DIR / "raw_absences.txt"
        raw_vacations_path = FIORILLI_DIR / "raw_vacations.txt"

        try:
            last_absences = self.read_csv(
                last_absences_path,
            )
        except FileNotFoundError:
            last_absences = pd.DataFrame
        try:
            all_absences = pd.concat(
                [
                    self.read_csv(raw_vacations_path),
                    self.read_csv(raw_absences_path),
                ]
            )
        except EmptyDataError:
            all_absences = pd.DataFrame

        return last_absences, all_absences

    def treat_exceptions_and_typos(self, text: str) -> str:
        if text == "VIGILACIA EM SAUDE":
            return "VIGILANCIA EM SAUDE"
        if text == "UBS SAO JOSE/CIDADE JARDIM":
            return "UBS CIDADE JARDIM"
        if text == "PREFEITURA MUNICIPAL DE NOVA SERRANA":
            return "SECRETARIA DE EDUCACAO"
        if text == "FINANCAS":
            return "SECRETARIA MUN. FINANCAS"
        return text
