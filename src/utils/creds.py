import os

from dotenv import load_dotenv
from InquirerPy import inquirer
from rich import print

from src.utils.constants import REQUIRED_VARS


class Creds:
    def __init__(self):
        self.load_or_create_env()

    def load_or_create_env(self):
        load_dotenv()

        missing_vars = [var for var in REQUIRED_VARS if os.getenv(var) is None]

        if missing_vars:
            print(f"Variáveis de ambiente faltando: {', '.join(missing_vars)}")
            self.create_missing_vars(missing_vars)
            load_dotenv()

        for var in REQUIRED_VARS:
            setattr(self, var.lower(), os.getenv(var))

        if not missing_vars:
            return "Variáveis de ambiente OK"

    def create_missing_vars(self, missing_vars):
        env_vars = {}

        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        env_vars[key] = value

        print("\nPor favor, insira as credenciais faltantes:")
        for var in missing_vars:
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

    @staticmethod
    def is_env_ok():
        load_dotenv()
        missing = [var for var in REQUIRED_VARS if os.getenv(var) is None]

        if missing:
            return False

        return True
