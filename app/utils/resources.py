from functools import cache
from importlib.resources import files
import json


@cache
def load_json(name: str):
    path = (
        files("resources.dictionaries")
        / f"{name}.json"
    )

    return json.loads(path.read_text(encoding="utf-8"))