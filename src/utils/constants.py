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
        {"key": "j"},
    ],
    "up": [
        {"key": "up"},
        {"key": "k"},
    ],
    "toggle": [
        {"key": "space"},
    ],
    "toggle-all-true": [
        {"key": "a"},
    ],
}


JSON_INIT_CONFIG = {
    "init_date": "",
    "headless_mode": True,
    "last_analisys": {"datetime": "", "time_since": ""},
    "last_download": {
        "ahgora_employees": {"datetime": "", "time_since": ""},
        "fiorilli_employees": {"datetime": "", "time_since": ""},
        "absences": {"datetime": "", "time_since": ""},
    },
}

MAIN_MENU_OPTIONS = [
    "Baixar Dados",
    "Analisar dados",
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

PT_WEEKDAYS = {
    "Mon": "Seg",
    "Tue": "Ter",
    "Wed": "Qua",
    "Thu": "Qui",
    "Fri": "Sex",
    "Sat": "Sáb",
    "Sun": "Dom",
}

REQUIRED_VARS = {
    "FIORILLI_USER": None,
    "FIORILLI_PSW": None,
    "AHGORA_USER": None,
    "AHGORA_PSW": None,
    "AHGORA_COMPANY": None,
}

ABSENCES_COLUMNS = [
    "id",
    "cod",
    "start_date",
    "start_time",
    "end_date",
    "end_time",
]
