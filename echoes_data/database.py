import json
import logging
import sqlite3
from sqlite3 import Error, Connection
from typing import Dict, Any, Tuple, Type, Optional

logger = logging.getLogger("eed.db")


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
        case "bool":
            return bool
        case "float":
            return float


def load_schema(file: str, schema: Optional[Dict] = None) -> Dict[str, Tuple[str, Type]]:
    with open(file, "r") as f:
        raw = json.load(f)
    if schema is None:
        schema = {}
    attributes = raw["valueTypes"]["attributes"]  # type: Dict[str, Dict[str, str]]
    for key in attributes:
        if key in schema:
            continue
        schema[key] = (snake_to_camel(key), to_type(attributes[key]["type"]))
    schema["key"] = ("id", int)
    return schema


class EchoesDB:
    def __init__(self) -> None:
        self.conn = None  # type: Connection | None

    def create_connection(self, db_file: str):
        """ create a database connection to a SQLite database """
        try:
            self.conn = sqlite3.connect(db_file)
        except Error as e:
            logger.error("Error while opening database", exc_info=e)

    def _insert_data(self, table: str, data: Dict[str, Any]):
        placeholders = ', '.join(['?'] * len(data))
        columns = ', '.join(data.keys())
        sql = "REPLACE INTO %s ( %s ) VALUES ( %s )" % (table, columns, placeholders)
        self.conn.execute(sql, list(data.values()))

    def load_data(self,
                  file: str,
                  table: str,
                  auto_schema=True,
                  schema: Optional[Dict[str, Tuple[str, Type]]] = None,
                  fields: Optional[str] = None):
        logger.info("Loading data from file %s into %s", file, table)
        with open(file, "r") as f:
            raw = json.load(f)
        if auto_schema:
            schema = load_schema(file.replace(".json", ".schema.json"), schema)

        if type(fields) == str:
            fields = fields.split(",")
        loaded = 0
        for key, value in raw.items():
            data = {schema["key"][0]: int(key)}
            for k, v in value.items():
                if schema[k][1] is None:
                    continue
                if fields is not None and schema[k][0] in fields:
                    conv = (schema[k][1])(v)
                    data[schema[k][0]] = conv
            self._insert_data(table, data)
            loaded += 1
        self.conn.commit()
        logger.info("Loaded %s rows into table %s from file %s", loaded, table, file)

    def setup_tables(self):
        self.conn.execute("create table if not exists attributes("
                          "    id                   INTEGER             not null primary key,"
                          "    attributeCategory    INTEGER             not null,"
                          "    attributeName        TEXT                not null,"
                          "    available            INTEGER             not null,"
                          "    chargeRechargeTimeId INTEGER             not null,"
                          "    defaultValue         REAL                not null,"
                          "    highIsGood           INTEGER             not null,"
                          "    maxAttributeId       INTEGER             not null,"
                          "    attributeOperator    TEXT                not null,"
                          "    stackable            INTEGER             not null,"
                          "    toAttrId             TEXT                not null,"
                          "    unitId               INTEGER             not null,"
                          "    unitLocalisationKey  INTEGER default 0,"
                          "    attributeSourceUnit  TEXT    default '',"
                          "    attributeTip         TEXT    default '',"
                          "    attributeSourceName  TEXT    default '',"
                          "    nameLocalisationKey  INTEGER default 0,"
                          "    tipLocalisationKey   INTEGER default 0,"
                          "    attributeFormula     TEXT    default 'A' not null"
                          ");"
                          )
