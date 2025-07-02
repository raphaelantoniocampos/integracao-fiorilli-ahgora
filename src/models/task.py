from pathlib import Path

from pandas import DataFrame


class Task:
    def __init__(
        self,
        name: str,
        path: Path,
        data: DataFrame | list[any],
        option: str,
    ):
        self.name = name
        self.path = path
        self.data = data
        self.option = option
        self.url = (
            "https://app.ahgora.com.br/funcionarios"
            if "leaves" not in name
            else "https://app.ahgora.com.br/afastamentos/importa"
        )

    def is_empty(self):
        try:
            return self.data.empty
        except AttributeError:
            return True

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return f"""
-name: {self.name}
-df: {self.data.head(5)}
-option: {self.option}
-"""
