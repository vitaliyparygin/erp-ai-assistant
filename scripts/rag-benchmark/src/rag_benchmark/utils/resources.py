"""Small shared utilities: logging setup, id/slug helpers, text helpers."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from pathlib import Path
from functools import cache
from importlib.resources import files
import json

_LOGGER_NAME = "rag_benchmark.utils.resources"
PACKAGE = "rag_benchmark.resources"


# @cache
# def load_json(group: str, name: str):
#     if not name.endswith(".json"):
#         name += ".json"
#
#     path = files(PACKAGE).joinpath(name)
#
#     if not path.is_file():
#         available = sorted(
#             p.name
#             for p in files(PACKAGE).iterdir()
#             if p.name.endswith(".json")
#         )
#
#         raise FileNotFoundError(
#             f"Dictionary '{name}' not found.\n"
#             f"Expected: {path}\n"
#             f"Available dictionaries: {available}"
#         )
#
#     return json.loads(
#         files(f"{PACKAGE}.{group}")
#         .joinpath(name)
#         .read_text(encoding="utf-8")
#     )

def resource(group: str, name: str):
    return files(f"{PACKAGE}.{group}").joinpath(name)

@cache
def load_json(group: str, name: str):
    path = resource(group, _with_suffix(name, ".json"))
    return json.loads(path.read_text("utf-8"))

# @cache
# def load_yaml(group: str, name: str):
#     path = resource(group, _with_suffix(name, ".yaml"))
#     return yaml.safe_load(path.read_text("utf-8"))


@cache
def load_text(group: str, name: str):
    return resource(group, name).read_text("utf-8")


def _with_suffix(name: str, suffix: str):
    return name if name.endswith(suffix) else name + suffix