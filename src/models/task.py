from pathlib import Path

from pandas import DataFrame


class Task:
    def __init__(self, name: str, path: Path, df: DataFrame, option: str):
        self.name = name
        self.path = path
        self.df = df
        self.option = option
        self.url = (
            "https://app.ahgora.com.br/funcionarios"
            if name != "add_absences"
            else "https://app.ahgora.com.br/afastamentos/importa"
        )

    def is_empty(self):
        try:
            return self.df.empty
        except AttributeError:
            return True

    def __len__(self):
        return len(self.df)

    def __str__(self):
        return f"""
-name: {self.name}
-df: {self.df.head(5)}
-option: {self.option}
-"""
