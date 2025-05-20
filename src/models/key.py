import time

import keyboard
from rich import print


class Key:
    def __init__(self, name: str, color: str, action: str):
        self.name = name
        self.color = color
        self.key = str(name)
        self.action = action
        self.desc = f"Pressione {self} para [bold white]{action.lower()}[/bold white]"

    def __str__(self):
        return f"[bold {self.color}]{self.name.upper()}[/bold {self.color}]"


def wait_key_press(keys: list[Key]):
    if isinstance(keys, Key):
        keys = [keys]
    for key in keys:
        print(key.desc)
    while True:
        for key in keys:
            if keyboard.is_pressed(key.key):
                time.sleep(0.5)
                return key.action
