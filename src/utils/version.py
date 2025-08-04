import tomllib


def get_project_version() -> str:
    """Reads and returns the project version from the pyproject.toml file."""
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except FileNotFoundError:
        return "unknown"
    except KeyError:
        return "unknown"
