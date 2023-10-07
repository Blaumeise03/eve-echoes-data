import functools
import json
import os
import typing
from typing import Type, Optional, Dict, Tuple, Union, Callable


def decapitalize(s, upper_rest=False):
    return ''.join([s[:1].lower(), (s[1:].upper() if upper_rest else s[1:])])


def snake_to_camel(value: str) -> str:
    return decapitalize("".join(x.capitalize() for x in value.lower().split("_")))


def to_type(string: str) -> Type:
    match string:
        case "string":
            return str
        case "int":
            return int
        case "long":
            return int
        case "bool":
            return bool
        case "float":
            return float
        case "list":
            return str


def load_schema(file: Union[str, os.PathLike], schema: Optional[Dict] = None) -> Dict[str, Tuple[str, Type]]:
    if not os.path.exists(file):
        return schema
    with open(file, "r") as f:
        raw = json.load(f)
    if schema is None:
        schema = {}
    attributes = raw["valueTypes"]["attributes"]  # type: Dict[str, Dict[str, str]]
    for key in attributes:
        if key in schema:
            continue
        schema[key] = (snake_to_camel(key), to_type(attributes[key]["type"]))
    if "key" not in schema:
        schema["key"] = ("id", int)
    return schema
