import json
import logging
import os
import re
import sqlite3
from sqlite3 import Error, Connection
from typing import Dict, Any, Tuple, Type, Optional, List

logger = logging.getLogger("ee.db")
name_regexp = re.compile(r"(\{([a-zA-Z_-]+:)[^{}]+})")
name_corrected_regexp = re.compile(r"(\{[^{}]+})")


def decapitalize(s, upper_rest=False):
    return ''.join([s[:1].lower(), (s[1:].upper() if upper_rest else s[1:])])


def snake_to_camel(value: str) -> str:
    return decapitalize("".join(x.capitalize() for x in value.lower().split("_")))


def correct_string(string: str):
    matches = re.finditer(name_regexp, string)
    for m in matches:
        string = string.replace(m.group(2), "")
    return string


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
        case "list":
            return str


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
        self.strings = {}  # type: Dict[str, int]
        self.new_loc_cache = {}

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

    def load_dict_data(self,
                       file: str,
                       table: str,
                       merge_with_file: Optional[str] = None,
                       auto_schema=True,
                       schema: Optional[Dict[str, Tuple[str, Type]]] = None,
                       fields: Optional[str] = None,
                       default_values: Optional[Dict[str, Any]] = None,
                       localized: Optional[Dict[str, str]] = None):
        logger.info("Loading data from file %s into %s", file, table)
        with open(file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        raw_extra = None
        if merge_with_file:
            with open(merge_with_file, "r", encoding="utf-8") as f:
                raw_extra = json.load(f)
        if auto_schema:
            schema = load_schema(file=file.replace(".json", ".schema.json"),
                                 schema=schema)
            if merge_with_file:
                load_schema(file=merge_with_file.replace(".json", ".schema.json") if merge_with_file else None,
                            schema=schema)

        if type(fields) == str:
            fields = fields.split(",")
        loaded = 0
        for key, item in raw.items():
            data = {schema["key"][0]: int(key)}
            for k, v in item.items():
                if schema[k][1] is None:
                    continue
                if fields is not None and schema[k][0] in fields:
                    data[schema[k][0]] = (schema[k][1])(v)
            if localized:
                for field, k in localized.items():
                    if k in data:
                        string = data[k]
                    else:
                        string = item[k]
                    string_c = correct_string(string)
                    if string == string_c:
                        data[field] = self.get_localized_id(string, save_new=True, only_cache=True)
                    else:
                        # Handle strings like "{module_affix:联邦海军} {module:大型装甲连接模块}"
                        # The placeholder will get replaced with the ids,
                        # e.g. "{43690} {3507}"
                        data[field] = -2
                        if k in data:
                            data[k] = self.correct_localized_string(string)

            # Load extra data from additional file
            if raw_extra and key in raw_extra:
                for k, v in raw_extra[key].items():
                    if schema[k][1] is None:
                        continue
                    if fields is not None and schema[k][0] in fields:
                        data[schema[k][0]] = (schema[k][1])(v)
            if default_values:
                for field, v in default_values.items():
                    if field not in data:
                        data[field] = v
            self._insert_data(table, data)
            loaded += 1
        self.conn.commit()
        logger.info("Loaded %s rows into table %s from file %s", loaded, table, file)
        self.save_localized_cache()

    def load_all_dict_data(self,
                           root_path: str,
                           table: str,
                           merge_with_file_path: Optional[str] = None,
                           auto_schema=True,
                           schema: Optional[Dict[str, Tuple[str, Type]]] = None,
                           fields: Optional[str] = None,
                           default_values: Optional[Dict[str, Any]] = None,
                           localized: Optional[Dict[str, str]] = None):
        directory = os.fsencode(root_path)
        logger.info("Loading data from dir %s into %s", root_path, table)
        count = 0
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if not re.match(r"\d+\.json", filename):
                continue
            file_2 = None
            if merge_with_file_path and os.path.exists(f"{merge_with_file_path}/{filename}"):
                file_2 = f"{merge_with_file_path}/{filename}"
            self.load_dict_data(
                file=f"{root_path}/{filename}", table=table, merge_with_file=file_2, auto_schema=auto_schema,
                schema=schema, fields=fields, default_values=default_values, localized=localized
            )
        logger.info("Loaded %s files into %s from %s", count, table, root_path)

    def _insert_batch_data(self, table: str, key_field: str, value_field: str, batch: List[Tuple[Any, Any, Any]]):
        sql = "INSERT INTO %s ( %s, %s ) VALUES ( ?, ? ) ON CONFLICT( %s ) DO UPDATE SET %s=?" % (
            table, key_field, value_field, key_field, value_field)
        self.conn.executemany(sql, batch)

    def load_simple_data(self,
                         file: str,
                         table: str,
                         key_field: str,
                         value_field: str,
                         key_type: Type = int,
                         value_type: Type = str,
                         second_value_field: Optional[str] = None,
                         save_lang=False):
        batch = []
        with open(file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for key, value in raw.items():
            batch.append((key_type(key), value_type(value), value_type(value)))
            if save_lang:
                self.strings[value_type(value)] = key_type(key)
        self._insert_batch_data(table, key_field, value_field, batch)
        if second_value_field:
            self._insert_batch_data(table, key_field, second_value_field, batch)
        self.conn.commit()

    def load_language(self, base_path: str, lang: str, copy_to: Optional[str] = None):
        directory = os.fsencode(f"{base_path}/{lang}")
        logger.info("Loading language %s into the database: %s", lang, f"{base_path}/{lang}")
        count = 0
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if not re.match(r"\d+\.json", filename):
                continue
            self.load_simple_data(
                file=f"{base_path}/{lang}/{filename}",
                table="localised_strings",
                key_field="id", value_field=lang,
                key_type=int, value_type=str, second_value_field=copy_to,
                save_lang=(lang == "zh")
            )
            count += 1
        logger.info("Loaded %s language files for language %s", count, lang)

    def get_next_loc_id(self):
        start = 5000000000
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM localised_strings WHERE id>=? ORDER BY ID DESC LIMIT 1;", (start,))
        res = cursor.fetchone()
        if res is not None:
            start = res[0] + 1
        return start

    def get_localized_id(self, zh_name: str, save_new=False, only_cache=True) -> int:
        if zh_name in self.strings:
            return self.strings[zh_name]
        res = None
        cursor = None
        if not only_cache:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM localised_strings WHERE source=?;", (zh_name,))
            res = cursor.fetchone()
        if res is None:
            if save_new:
                next_id = self.get_next_loc_id()
                if not only_cache:
                    cursor.execute("INSERT INTO localised_strings ( id, source ) VALUES ( ?, ? )", (next_id, zh_name))
                    logger.info("Localized string for '%s' not found, saved as id %s", zh_name, next_id)
                self.strings[zh_name] = next_id
                if only_cache:
                    self.new_loc_cache[zh_name] = next_id
                return next_id
            else:
                logger.warning("Localized string for '%s' not found", zh_name)
                return -1
        self.strings[zh_name] = res[0]
        return res[0]

    def load_localized_cache(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, source FROM localised_strings")
        res = cursor.fetchall()
        for s_id, source in res:
            self.strings[source] = s_id
        logger.info("Loaded %s localized strings into the database", len(res))

    def save_localized_cache(self):
        if len(self.new_loc_cache) == 0:
            return
        batch = [(v, k, k) for k, v in self.new_loc_cache.items()]
        self._insert_batch_data(table="localised_strings", key_field="id", value_field="source", batch=batch)
        self.new_loc_cache.clear()
        logger.info("Saved %s new localised strings from cache into the database", len(batch))

    def correct_localized_string(self, string: str):
        matches = re.finditer(name_corrected_regexp, string)
        for m in matches:
            string = string.replace(m.group(2), str(self.get_localized_id(m.group(2), save_new=True, only_cache=True)))
        return string

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
                          "    attributeFormula     TEXT    default 'A' not null);")
        self.conn.execute("create table if not exists effects("
                          "    id                            INTEGER           not null primary key,"
                          "    disallowAutoRepeat            INTEGER default 0 not null,"
                          "    dischargeAttributeId          INTEGER default 0 not null,"
                          "    durationAttributeId           INTEGER default 0 not null,"
                          "    effectCategory                INTEGER default 0 not null,"
                          "    effectName                    TEXT              not null,"
                          "    electronicChance              INTEGER default 0 not null,"
                          "    falloffAttributeId            INTEGER default 0 not null,"
                          "    fittingUsageChanceAttributeId INTEGER default 0 not null,"
                          "    guid                          TEXT              not null,"
                          "    isAssistance                  INTEGER default 0 not null,"
                          "    isOffensive                   INTEGER default 0 not null,"
                          "    isWarpSafe                    INTEGER default 0 not null,"
                          "    rangeAttributeId              INTEGER default 0 not null,"
                          "    rangeChance                   INTEGER default 0 not null,"
                          "    trackingSpeedAttributeId      INTEGER default 0 not null);")
        self.conn.execute("create table if not exists unit("
                          "    id          INTEGER primary key,"
                          "    description TEXT,"
                          "    displayName TEXT,"
                          "    unitName    TEXT );")
        self.conn.execute("create table if not exists localised_strings("
                          "    id     INTEGER primary key,"
                          "    source TEXT,"
                          "    en     TEXT,"
                          "    de     TEXT,"
                          "    fr     TEXT,"
                          "    ja     TEXT,"
                          "    kr     TEXT,"
                          "    por    TEXT,"
                          "    ru     TEXT,"
                          "    spa    TEXT,"
                          "    zh     TEXT,"
                          "    zhcn   TEXT);")
        self.conn.execute("create table if not exists groups("
                          "    id                   INTEGER primary key,"
                          "    anchorable           INTEGER not null,"
                          "    anchored             INTEGER not null,"
                          "    fittableNonSingleton INTEGER not null,"
                          "    iconPath             TEXT,"
                          "    useBasePrice         INTEGER not null,"
                          "    localisedNameIndex   INTEGER not null,"
                          "    sourceName           TEXT,"
                          "    itemIds              TEXT );")
        self.conn.execute("create table if not exists categories("
                          "    id                 INTEGER primary key,"
                          "    groupIds           TEXT,"
                          "    localisedNameIndex INTEGER default 0 not null,"
                          "    sourceName         TEXT"
                          ");")
        self.conn.execute("create table if not exists items("
                          "    id                 INTEGER primary key,"
                          "    canBeJettisoned    INTEGER            not null,"
                          "    descSpecial        TEXT               not null,"
                          "    mainCalCode        TEXT    default '' not null,"
                          "    onlineCalCode      TEXT    default '',"
                          "    activeCalCode      TEXT    default '',"
                          "    sourceDesc         TEXT               not null,"
                          "    sourceName         TEXT               not null,"
                          "    nameKey            INTEGER            not null,"
                          "    descKey            INTEGER            not null,"
                          "    marketGroupId      INTEGER,"
                          "    lockSkin           TEXT,"
                          "    npcCalCodes        TEXT,"
                          "    product            INTEGER,"
                          "    exp                REAL    default 0  not null,"
                          "    published          INTEGER default 0  not null,"
                          "    preSkill           TEXT,"
                          "    corpCamera         TEXT               not null,"
                          "    abilityList        TEXT               not null,"
                          "    normalDebris       TEXT               not null,"
                          "    shipBonusCodeList  TEXT               not null,"
                          "    shipBonusSkillList TEXT               not null"
                          ");")
