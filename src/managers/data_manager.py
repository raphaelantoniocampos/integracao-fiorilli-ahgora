import unicodedata
from datetime import datetime
from time import sleep

import pandas as pd
from pandas.errors import EmptyDataError
from rich import print

from src.managers.file_manager import FileManager as file_manager
from src.utils.config import Config
from src.utils.constants import DATA_DIR, PT_MONTHS
from src.utils.ui import console

ABSENCES_COLUMNS = [
    "id",
    "cod",
    "start_date",
    "start_time",
    "end_date",
    "end_time",
]


class DataManager:
    def analyze(self) -> (pd.DataFrame, pd.DataFrame):
        try:
            ()
            with console.status(
                "[bold green]Analisando dados...[/bold green]", spinner="dots"
            ):
                ahgora_employees, fiorilli_employees = self.get_employees_data()
                last_absences, all_absences = self.get_absences_data()

                file_manager.save_df(
                    df=ahgora_employees,
                    path=DATA_DIR / "ahgora" / "employees.csv",
                )
                file_manager.save_df(
                    df=fiorilli_employees,
                    path=DATA_DIR / "fiorilli" / "employees.csv",
                )

                file_manager.save_df(
                    df=all_absences,
                    path=DATA_DIR / "fiorilli" / "absences.csv",
                    header=False,
                )

                self.generate_tasks_dfs(
                    fiorilli_employees=fiorilli_employees,
                    ahgora_employees=ahgora_employees,
                    last_absences=last_absences,
                    all_absences=all_absences,
                )

            Config.update_last_analisys()
            print("[bold green]Dados sincronizados com sucesso![/bold green]\n")
            sleep(1)
        except KeyboardInterrupt as e:
            print(f"[bold red]Erro ao sincronizar dados: {e}[/bold red]\n")
            sleep(1)

        except FileNotFoundError as e:
            print(
                f"[bold red]Erro ao analisar dados: {e}[/bold red]\nFaça do download primeiro."
            )
            sleep(1)

    @staticmethod
    def filter_df(df: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
        return df[df["id"].isin(ids)]

    def read_csv(
        self,
        path: str,
        sep: str = ",",
        encoding: str = "utf-8",
        header: str | None = "infer",
        columns: list[str] = [],
    ):
        df = pd.read_csv(
            path,
            sep=sep,
            encoding=encoding,
            index_col=False,
            header=header,
        )
        return self.prepare_dataframe(df=df, columns=columns)

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
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
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
            return pd.to_datetime(date_str, format="%d/%b/%Y", errors="raise")
        except ValueError:
            try:
                return pd.to_datetime(date_str, format="%d/%m/%Y", errors="raise")
            except ValueError:
                try:
                    return pd.to_datetime(
                        date_str, format="%d/%b/%Y %H:%M", errors="raise"
                    )
                except ValueError:
                    return pd.to_datetime(date_str, format="ISO8601", errors="coerce")

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
            dismissed_employees_df["dismissal_date"], format="%d/%m/%Y"
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

        columns_to_check = ["position", "department"]
        for col in columns_to_check:
            merged_employees[f"{col}_fiorilli_norm"] = merged_employees[
                f"{col}_fiorilli"
            ].apply(self.normalize_text)
            merged_employees[f"{col}_ahgora_norm"] = merged_employees[
                f"{col}_ahgora"
            ].apply(self.normalize_text)

        position_changed = (
            merged_employees["position_fiorilli_norm"]
            != merged_employees["position_ahgora_norm"]
        )
        location_changed = (
            merged_employees["department_fiorilli_norm"]
            != merged_employees["department_ahgora_norm"]
        )
        changed_employees_df = merged_employees[position_changed | location_changed]

        return changed_employees_df

    def _get_new_absences_df(
        self,
        last_absences: pd.DataFrame,
        all_absences: pd.DataFrame,
    ) -> pd.DataFrame:
        try:
            merged = pd.merge(last_absences, all_absences, how="outer", indicator=True)

            new_absences = merged[merged["_merge"] == "right_only"].drop(
                "_merge", axis=1
            )
        except TypeError:
            new_absences = all_absences
        return new_absences

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
        save_dir = DATA_DIR / "tasks"

        file_manager.save_df(
            df=new_employees_df,
            path=save_dir / "new_employees.csv",
        )
        file_manager.save_df(
            df=dismissed_employees_df,
            path=save_dir / "dismissed_employees.csv",
        )
        file_manager.save_df(
            df=changed_employees_df,
            path=save_dir / "changed_employees.csv",
        )
        file_manager.save_df(
            df=new_absences_df,
            path=save_dir / "new_absences.csv",
        )

    def get_employees_data(self) -> (pd.DataFrame, pd.DataFrame):
        raw_fiorilli_employees = DATA_DIR / "fiorilli" / "raw_employees.txt"
        raw_ahgora_employees = DATA_DIR / "ahgora" / "raw_employees.csv"

        fiorilli_employees = self.read_csv(
            raw_fiorilli_employees,
            sep="|",
            encoding="latin1",
            header=None,
            columns=[
                "id",
                "name",
                "cpf",
                "sex",
                "birth_date",
                "pis_pasep",
                "position",
                "department",
                "cost_center",
                "binding",
                "admission_date",
                "dismissal_date",
            ],
        )

        ahgora_employees = self.read_csv(
            raw_ahgora_employees,
            header=None,
            columns=[
                "id",
                "name",
                "position",
                "scale",
                "department",
                "location",
                "admission_date",
                "dismissal_date",
            ],
        )
        return ahgora_employees, fiorilli_employees

    def get_absences_data(self) -> pd.DataFrame:
        last_absences_path = DATA_DIR / "tasks" / "absences.csv"
        raw_absences_path = DATA_DIR / "fiorilli" / "raw_absences.txt"
        raw_vacations_path = DATA_DIR / "fiorilli" / "raw_vacations.txt"

        try:
            last_absences = self.read_csv(
                last_absences_path,
                header=None,
                columns=ABSENCES_COLUMNS,
            )
        except FileNotFoundError:
            last_absences = pd.DataFrame
        try:
            all_absences = pd.concat(
                [
                    self.read_csv(
                        raw_vacations_path,
                        header=None,
                        columns=ABSENCES_COLUMNS,
                    ),
                    self.read_csv(
                        raw_absences_path,
                        header=None,
                        columns=ABSENCES_COLUMNS,
                    ),
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
