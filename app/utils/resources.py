from functools import cache
from importlib.resources import files
import json
from app.resources import dictionaries


@cache
def load_json(name: str):
    if not name.endswith(".json"):
        name += ".json"

    return json.loads(
        files(dictionaries)
        .joinpath(name)
        .read_text(encoding="utf-8")
    )