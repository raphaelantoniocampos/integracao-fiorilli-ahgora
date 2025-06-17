from pathlib import Path

# Program diresctories

BASE_DIR = Path(Path.cwd())
DATA_DIR = BASE_DIR / "data"
DOWNLOADS_DIR = BASE_DIR / "downloads"
FIORILLI_DIR = DATA_DIR / "fiorilli"
AHGORA_DIR = DATA_DIR / "ahgora"
TASKS_DIR = BASE_DIR / "tasks"

INQUIRER_KEYBINDINGS = {
    "answer": [
        {"key": "enter"},
    ],
    "interrupt": [
        {"key": "c-c"},
        {"key": "c-e"},
    ],
    "skip": [
        {"key": "c-z"},
        {"key": "escape"},
    ],
    "down": [
        {"key": "down"},
    ],
    "up": [
        {"key": "up"},
    ],
}


JSON_INIT_CONFIG = {
    "init_date": "",
    "headless_mode": True,
    "last_analisys": {"datetime": "", "time_since": ""},
    "last_download": {
        "ahgora_employees": {"datetime": "", "time_since": ""},
        "fiorilli_employees": {"datetime": "", "time_since": ""},
        "leaves": {"datetime": "", "time_since": ""},
    },
}

MAIN_MENU_OPTIONS = [
    "Downloads",
    "Dados",
    "Tarefas",
    "Configurações",
    "Sair",
]

PT_MONTHS = {
    "Jan": "Jan",
    "Fev": "Feb",
    "Mar": "Mar",
    "Abr": "Apr",
    "Mai": "May",
    "Jun": "Jun",
    "Jul": "Jul",
    "Ago": "Aug",
    "Set": "Sep",
    "Out": "Oct",
    "Nov": "Nov",
    "Dez": "Dec",
}

REQUIRED_VARS = {
    "FIORILLI_USER": None,
    "FIORILLI_PSW": None,
    "AHGORA_USER": None,
    "AHGORA_PSW": None,
    "AHGORA_COMPANY": None,
}

UPLOAD_LEAVES_COLUMNS = [
    "id",
    "cod",
    "start_date",
    "start_time",
    "end_date",
    "end_time",
]

LEAVES_COLUMNS = [
    "id",
    "name",
    "cod",
    "cod_name",
    "start_date",
    "end_date",
    "duration",
    "start_time",
    "end_time",
]

RAW_AHGORA_EMPLOYEES_COLUMNS = [
    "id",
    "name",
    "position",
    "scale",
    "department",
    "location",
    "admission_date",
    "dismissal_date",
]

RAW_FIORILLI_EMPLOYEES_COLUMNS = [
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
]
