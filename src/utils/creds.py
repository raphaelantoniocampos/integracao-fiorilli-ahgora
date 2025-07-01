import os

from dotenv import load_dotenv
from InquirerPy import inquirer
from rich import print

from src.utils.constants import REQUIRED_VARS


class Creds:
    def load_vars(self):
        for var in REQUIRED_VARS:
            setattr(self, var.lower(), os.getenv(var))
        load_dotenv()

    @staticmethod
    def get_missing_vars():
        load_dotenv()

        missing_vars = [var for var in REQUIRED_VARS if os.getenv(var) is None]

        if not missing_vars:
            missing_vars = []

        return missing_vars

    @staticmethod
    def create_vars(vars):
        env_vars = {}

        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        env_vars[key] = value

        print("\nPor favor, insira as credenciais faltantes:")
        for var in vars:
            env_vars[var] = (
                inquirer.text(message=f"{var}: ", is_password="PASSWORD" in var)
                .execute()
                .strip()
            )

        try:
            with open(".env", "w") as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            print("\nArquivo .env atualizado com sucesso!")
        except Exception as e:
            print(f"\nErro ao salvar no arquivo .env: {e}")
