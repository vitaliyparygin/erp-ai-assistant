from functools import cache
from importlib.resources import files
import json
from app.resources import dictionaries


@cache
def load_json(name: str):
    if not name.endswith(".json"):
        name += ".json"

    path = files(dictionaries).joinpath(name)

    if not path.is_file():
        available = sorted(
            p.name
            for p in files(dictionaries).iterdir()
            if p.name.endswith(".json")
        )

        raise FileNotFoundError(
            f"Dictionary '{name}' not found.\n"
            f"Expected: {path}\n"
            f"Available dictionaries: {available}"
        )

    return json.loads(path.read_text(encoding="utf-8"))