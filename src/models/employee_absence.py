from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class AbsenceDataParser(ABC):
    @abstractmethod
    def parse(self, line: str) -> dict:
        pass


class EmployeeRepository(ABC):
    @abstractmethod
    def get_employee_name(self, employee_id: str) -> str:
        pass


class DateConverter(ABC):
    @staticmethod
    @abstractmethod
    def convert(date_str: str, time_str: str) -> datetime:
        pass


# Implementações Concretas


class EmployeeAbsenceRawParser(AbsenceDataParser):
    def parse(self, line: str) -> dict:
        line_splitted = [item.strip() for item in line.split(",")]
        return {
            "id": line_splitted[0],
            "cod": line_splitted[1],
            "start_date_str": line_splitted[2],
            "start_time_str": line_splitted[3],
            "end_date_str": line_splitted[4],
            "end_time_str": line_splitted[5].strip(),
        }


class CSVEmployeeRepository(EmployeeRepository):
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)
        # Supondo que o CSV tem colunas 'matricula' e 'nome'
        self.employee_map = dict(zip(self.df["matricula"], self.df["nome"]))

    def get_employee_name(self, employee_id: str) -> str:
        return self.employee_map.get(employee_id, "Nome não encontrado")


class StandardDateConverter(DateConverter):
    DATE_FORMAT = "%d/%m/%Y"
    TIME_FORMAT = "%H:%M"

    @staticmethod
    def convert(date_str: str, time_str: str) -> datetime:
        return datetime.strptime(
            f"{date_str} {time_str}",
            f"{StandardDateConverter.DATE_FORMAT} {StandardDateConverter.TIME_FORMAT}",
        )


# Classes de Domínio


class EmployeeAbsence:
    def __init__(self, id: str, cod: str):
        self.id = id
        self.cod = cod

    def __str__(self) -> str:
        return f"ID: {self.id}, Code: {self.cod}"


class EmployeeAbsenceFull(EmployeeAbsence):
    def __init__(
        self, id: str, name: str, cod: str, start_date: datetime, end_date: datetime
    ):
        super().__init__(id, cod)
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.duration = end_date - start_date

    def __str__(self) -> str:
        base_info = super().__str__()
        return (
            f"{base_info}, Name: {self.name}, "
            f"Start: {self.start_date.strftime('%d/%m/%Y %H:%M')}, "
            f"End: {self.end_date.strftime('%d/%m/%Y %H:%M')}, "
            f"Duration: {self.duration.days} dias"
        )


# Serviço para processar ausências


class AbsenceProcessor:
    def __init__(
        self,
        parser: AbsenceDataParser,
        date_converter: DateConverter,
        employee_repo: EmployeeRepository,
    ):
        self.parser = parser
        self.date_converter = date_converter
        self.employee_repo = employee_repo

    def process_raw_absence(self, line: str) -> EmployeeAbsence:
        data = self.parser.parse(line)
        return EmployeeAbsence(data["id"], data["cod"])

    def process_full_absence(self, line: str) -> EmployeeAbsenceFull:
        data = self.parser.parse(line)
        start_date = self.date_converter.convert(
            data["start_date_str"], data["start_time_str"]
        )
        end_date = self.date_converter.convert(
            data["end_date_str"], data["end_time_str"]
        )
        employee_name = self.employee_repo.get_employee_name(data["id"])

        return EmployeeAbsenceFull(
            id=data["id"],
            name=employee_name,
            cod=data["cod"],
            start_date=start_date,
            end_date=end_date,
        )


# Função principal


def main():
    # Exemplo de uso
    lines = [
        "032227, 115, 01/05/2025, 00:00, 30/04/2027, 24:00",
        "032228, 116, 01/06/2025, 08:00, 30/06/2025, 18:00",
    ]

    # Configuração das dependências
    parser = EmployeeAbsenceRawParser()
    date_converter = StandardDateConverter()
    employee_repo = CSVEmployeeRepository("data/fiorilli/employees.csv")
    processor = AbsenceProcessor(parser, date_converter, employee_repo)

    # Processando as linhas
    absences_full = [processor.process_full_absence(line) for line in lines]

    # Imprimindo os resultados
    print("Lista Completa de Ausências:")
    for i, absence in enumerate(absences_full, 1):
        print(f"{i}. {absence}")


if __name__ == "__main__":
    main()
