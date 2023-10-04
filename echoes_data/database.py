import functools
import json
import logging
import os
import re
from contextlib import closing
from enum import Enum
from typing import Dict, Any, Tuple, Type, Optional, List, Union, Callable, Iterable, Set

from sqlalchemy import Engine, Table, insert, delete, select, text, TextClause, Connection, Row

from echoes_data import models, utils

logger = logging.getLogger("ee.db")
name_regexp = re.compile(r"(\{([a-zA-Z_-]+:)[^{}]+})")
name_corrected_regexp = re.compile(r"(\{[^{}]+})")


class DataException(Exception):
    pass


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


def context_cursor(func: Callable):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # args[0] is self = EchoesDB
        with closing(args[0].conn.cursor()) as cursor:
            res = func(args[0], cursor, *args[1:], **kwargs)
        return res

    return _wrapper


class Dialect(Enum):
    sqlite = 1
    mysql = 2

    def replace(self, table: str, keys: Iterable[str]) -> TextClause:
        placeholders = ", ".join(map(lambda s: f":{s}", keys))
        columns = ", ".join(keys)
        return text("REPLACE INTO %s ( %s ) VALUES ( %s )" % (table, columns, placeholders))

    def upsert(self, table: str, keys: Iterable[str]):
        placeholders = ", ".join(map(lambda s: f":{s}", keys))
        columns = ", ".join(keys)
        set_ = ", ".join(map(lambda s: f"{s}=:{s}", keys))
        if self == Dialect.sqlite:
            return text(
                f"INSERT INTO {table} ( {columns} ) "
                f"  VALUES ( {placeholders} ) "
                f"  ON CONFLICT DO UPDATE SET {set_}"
            )
        elif self == Dialect.mysql:
            return text(
                f"INSERT INTO {table} ( {columns}) "
                f"  VALUES ( {placeholders}  ) ON DUPLICATE KEY UPDATE {set_}"
            )
        raise DataException(f"Unknown dialect {self}")

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Dialect) and __o.value == self.value

    @classmethod
    def from_str(cls, string: str):
        match string:
            case "sqlite":
                return Dialect.sqlite
            case "mysql":
                return Dialect.mysql


class EchoesDB:
    def __init__(self, engine: Engine, dialect: Dialect) -> None:
        self.engine = engine
        self.strings_en = {}  # type: Dict[int, str]
        self.strings = {}  # type: Dict[str, int]
        self.new_loc_cache = {}
        self.dialect = dialect

    def init_db(self):
        tables = [
            models.Region.__table__,
            models.Constellation.__table__,
            models.Solarsystem.__table__,
            models.SystemConnections,
            models.Celestial.__table__,
            models.Unit.__table__,
            models.LocalizedString.__table__,
            models.Attribute.__table__,
            models.Effect.__table__,
            models.Group.__table__,
            models.Categories.__table__,
            models.Type.__table__,
            models.Item.__table__,
            models.ItemNanocore.__table__,
            models.ItemAttribute.__table__,
            models.ItemEffects.__table__,
            models.PlanetExploit.__table__,
            models.ModifierDefinition.__table__,
            models.ModifierValue.__table__,
            models.ItemModifiers.__table__,
            models.RepackageVolume.__table__,
            models.Reprocess.__table__,
            models.Blueprint.__table__,
            models.BlueprintCosts.__table__
        ]
        logger.info("Setting up %s tables", len(tables))
        for table in tables:  # type: Table
            table.create(bind=self.engine, checkfirst=True)

    def _insert_data(self, table: str, data: Dict[str, Any], conn: Connection):
        stmt = self.dialect.upsert(table, data.keys())
        conn.execute(stmt, data)

    def load_dict_data(self,
                       file: str,
                       table: str,
                       merge_with_file: Optional[str] = None,
                       auto_schema=True,
                       schema: Optional[Dict[str, Tuple[str, Type]]] = None,
                       zero_none_fields: Optional[List[str]] = None,
                       fields: Optional[str] = None,
                       default_values: Optional[Dict[str, Any]] = None,
                       localized: Optional[Dict[str, str]] = None,
                       dict_root_key: Optional[str] = None,
                       skip: Union[List[Any], Set[Any], None] = None,
                       primary_key: Optional[str] = None):
        logger.info("Loading data from file %s into %s", file, table)
        with self.engine.connect() as conn:
            with open(file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            raw_extra = None
            if merge_with_file:
                with open(merge_with_file, "r", encoding="utf-8") as f:
                    raw_extra = json.load(f)
            if auto_schema:
                # Load json schema from the corresponding *.schema.json
                # The keys will be converted to camelCase
                schema = load_schema(file=file.replace(".json", ".schema.json"),
                                     schema=schema)
                if merge_with_file:
                    load_schema(file=merge_with_file.replace(".json", ".schema.json") if merge_with_file else None,
                                schema=schema)

            if type(fields) == str:
                fields = fields.split(",")
            loaded = 0
            if dict_root_key:
                for k in dict_root_key.split("."):
                    raw = raw[k]
            num = len(raw)
            # iterate all items in file
            for item_id, item in raw.items():
                data = {schema["key"][0]: schema["key"][1](item_id)}
                if skip is not None and data[primary_key] in skip:
                    continue
                # Iterate all properties of the item
                for k, v in item.items():
                    if schema[k][1] is None:
                        # Unknown data type
                        continue
                    # Check if property should get saved into the database
                    if fields is not None and schema[k][0] in fields:
                        data[schema[k][0]] = (schema[k][1])(v)
                        # Replace  with
                        if schema[k][1] == str:
                            data[schema[k][0]] = data[schema[k][0]].replace("'", "\"")
                if localized:
                    # Handle localized strings
                    for field, k in localized.items():
                        # field is the column of the database, k the property key
                        if k in data:
                            string = data[k]
                        else:
                            string = item[k]
                        string_c = correct_string(string)
                        if string == string_c:
                            # It is a normal string that can be handled directly
                            data[field] = self.get_localized_id(string, save_new=True, only_cache=True)
                        else:
                            # Handle strings like "{module_affix:联邦海军} {module:大型装甲连接模块}"
                            # The placeholder will get replaced with the ids,
                            # for example "{43690} {3507}".
                            # The key will be set to -2 as multiple keys were used.
                            data[field] = None
                            if k in data:
                                data[k] = self.correct_localized_string(string)

                # Load extra data from additional file.
                # For example, the items have an additional item_dogma file with extra properties.
                if raw_extra and item_id in raw_extra:
                    for k, v in raw_extra[item_id].items():
                        if schema[k][1] is None:
                            continue
                        if fields is not None and schema[k][0] in fields:
                            data[schema[k][0]] = (schema[k][1])(v)
                if default_values:
                    for field, v in default_values.items():
                        if field not in data:
                            data[field] = v
                if zero_none_fields is not None:
                    for k in zero_none_fields:
                        if k not in data:
                            continue
                        data[k] = data[k] if data[k] != 0 else None
                self.save_localized_cache(conn)
                self._insert_data(table, data, conn)
                if num > 3000 and loaded % 100 == 0:
                    utils.print_loading_bar(loaded / num)
                loaded += 1
            logger.info("Loaded %s rows into table %s from file %s", loaded, table, file)
            conn.commit()

    def load_all_dict_data(self,
                           root_path: str,
                           table: models.Base,
                           regex: Optional[re.Pattern] = None,
                           merge_with_file_path: Optional[str] = None,
                           auto_schema=True,
                           schema: Optional[Dict[str, Tuple[str, Type]]] = None,
                           fields: Optional[str] = None,
                           default_values: Optional[Dict[str, Any]] = None,
                           localized: Optional[Dict[str, str]] = None,
                           skip_existing=False,
                           primary_key: Optional[str] = None):
        directory = os.fsencode(root_path)
        logger.info("Loading data from dir %s into %s", root_path, table)
        count = 0
        if regex is None:
            regex = re.compile(r"\d+\.json")
        existing = set()
        if skip_existing:
            stmt = select(getattr(table, primary_key))
            with self.engine.connect() as conn:
                res = conn.execute(stmt).fetchall()
            for t in res:
                existing.add(t[0])
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if not re.match(regex, filename):
                continue
            file_2 = None
            if merge_with_file_path and os.path.exists(f"{merge_with_file_path}/{filename}"):
                file_2 = f"{merge_with_file_path}/{filename}"
            self.load_dict_data(
                file=f"{root_path}/{filename}", table=table.__tablename__, merge_with_file=file_2, auto_schema=auto_schema,
                schema=schema, fields=fields, default_values=default_values, localized=localized, skip=existing,
                primary_key=primary_key
            )
            count += 1
        logger.info("Loaded %s files into %s from %s", count, table, root_path)

    def _insert_batch_data(self, table: str, value_field: str, batch: List[Dict[str, Any]], conn: Optional[Connection] = None):
        if len(batch) == 0:
            return
        # noinspection PyTypeChecker
        keys = batch[0].keys()  # type: List[str]
        if conn is None:
            with self.engine.connect() as conn:
                stmt = self.dialect.upsert(table, keys)
                conn.execute(stmt, batch)
                conn.commit()
        else:
            stmt = self.dialect.upsert(table, keys)
            conn.execute(stmt, batch)
            conn.commit()

    def load_simple_data(self,
                         file: str,
                         table: str,
                         key_field: str,
                         value_field: str,
                         key_type: Type = int,
                         value_type: Type = str,
                         second_value_field: Optional[str] = None,
                         save_lang=False,
                         root_key: Optional[str] = None,
                         logging=False):
        batch = []
        with open(file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if root_key is not None:
            for k in root_key.split("."):
                raw = raw[k]
        for key, value in raw.items():
            if second_value_field is None:
                batch.append({
                    key_field: key_type(key), value_field: value_type(value)
                })
            else:
                batch.append({
                    key_field: key_type(key), value_field: value_type(value), second_value_field: value_type(value)
                })
            if save_lang:
                self.strings[value_type(value)] = key_type(key)
        self._insert_batch_data(table, value_field, batch)
        if second_value_field:
            self._insert_batch_data(table, second_value_field, batch)
        if logging:
            logger.info("Inserted %s rows from %s : %s into %s", len(batch), file, root_key, table)

    def load_language(self, base_path: str, lang: str, copy_to: Optional[str] = None):
        directory = os.fsencode(f"{base_path}/{lang}")
        count = 0
        files = list(filter(lambda f: re.match(r"\d+\.json", f), map(lambda f: os.fsdecode(f), os.listdir(directory))))
        num = len(files)
        logger.info("Loading language %s from %s files into the database from %s", lang, num, f"{base_path}/{lang}")
        for filename in files:
            self.load_simple_data(
                file=f"{base_path}/{lang}/{filename}",
                table="localised_strings",
                key_field="id", value_field=lang,
                key_type=int, value_type=str, second_value_field=copy_to,
                save_lang=(lang == "zh")
            )
            utils.print_loading_bar(count / num)
            count += 1
        logger.info("Loaded %s language files for language %s", count, lang)

    def get_next_loc_id(self):
        start = 5000000000
        with self.engine.connect() as conn:
            stmt = (
                select(models.LocalizedString.id)
                .where(models.LocalizedString.id >= start)
                .order_by(models.LocalizedString.id.desc())
                .limit(1)
            )
            res = conn.execute(stmt).fetchone()
        if res is not None:
            start = res[0] + 1
        return start

    def get_localized_id(self, zh_name: str, save_new=False, only_cache=True) -> int:
        if zh_name in self.strings:
            return self.strings[zh_name]
        res = None
        if not only_cache:
            with self.engine.connect() as conn:
                stmt = select(models.LocalizedString.id).where(models.LocalizedString.source == zh_name)
                res = conn.execute(stmt).fetchone()
        if res is None:
            if save_new:
                next_id = self.get_next_loc_id()
                if not only_cache:
                    with self.engine.connect() as conn:
                        stmt = insert(models.LocalizedString).values(id=next_id, source=zh_name)
                        conn.execute(stmt)
                        conn.commit()
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

    def get_localized_string(self, zh_name: str, return_def=True):
        if zh_name not in self.strings:
            if return_def:
                return zh_name
            return None
        return self.strings_en[self.strings[zh_name]]

    def load_localized_cache(self):
        with self.engine.connect() as conn:
            stmt = select(models.LocalizedString.id, models.LocalizedString.source, models.LocalizedString.en)
            res = conn.execute(stmt).fetchall()
            for s_id, source, en in res:
                self.strings[source] = s_id
                self.strings_en[s_id] = en
            logger.info("Loaded %s localized strings into the cache", len(res))

    def save_localized_cache(self, conn: Connection):
        if len(self.new_loc_cache) == 0:
            return
        batch = [{"id": v, "source": k} for k, v in self.new_loc_cache.items()]
        self._insert_batch_data(table="localised_strings", value_field="source", batch=batch, conn=conn)
        self.new_loc_cache.clear()
        # logger.info("Saved %s new localised strings from cache into the database", len(batch))

    def correct_localized_string(self, string: str):
        matches = re.finditer(name_corrected_regexp, string)
        for m in matches:
            string = string.replace(m.group(2), str(self.get_localized_id(m.group(2), save_new=True, only_cache=True)))
        return string

    def load_item_attributes(self, file: str, table: str, columns: Tuple[str, str, str]):
        with open(file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        batch = []
        for item_id, attrs in raw.items():
            for attr, value in attrs.items():
                batch.append({columns[0]: int(item_id), columns[1]: int(attr), columns[2]: value})
        # sql = f"INSERT INTO {table} ( {columns[0]}, {columns[1]}, {columns[2]} ) VALUES ( ?, ?, ? ) ON CONFLICT DO UPDATE SET {columns[2]}=?"
        with self.engine.connect() as conn:
            stmt = self.dialect.upsert(table, columns)
            conn.execute(stmt, batch)
        logger.info("Saved %s rows into table %s from file %s", len(batch), table, file)

    def load_all_item_attributes(self,
                                 root_path: str,
                                 table: str,
                                 columns: Tuple[str, str, str],
                                 regex: Optional[re.Pattern] = None
                                 ):
        directory = os.fsencode(root_path)
        logger.info("Loading data from dir %s into %s", root_path, table)
        count = 0
        if regex is None:
            regex = re.compile(r"\d+\.json")
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if not re.match(regex, filename):
                continue
            self.load_item_attributes(file=f"{root_path}/{filename}", table=table, columns=columns)
            count += 1
        logger.info("Saved %s files from %s into %s", count, root_path, table)

    def init_item_mod(self, item_mod_data: Union[List[Union[str, Any]], Row[Tuple]], columns_order: List[str], conn: Connection):
        def _clean(string: str) -> str:
            return string.lstrip("[").rstrip("]").replace("\"", "").replace(" ", "")
        stmt = self.dialect.upsert(models.ItemModifiers.__tablename__,
                                   ["code", "typeCode", "changeType", "attributeOnly",
                                    "changeRange", "changeRangeModuleNameId", "attributeId", "attributeValue"])
        code = item_mod_data[columns_order.index("code")]
        type_code = item_mod_data[columns_order.index("typeCode")]
        attribute_only = item_mod_data[columns_order.index("attributeOnly")]
        i = 0
        for change_type, change_range, attr_id, attr_val in zip(
                _clean(item_mod_data[columns_order.index("changeTypes")]).split(","),
                _clean(item_mod_data[columns_order.index("changeRanges")]).split(","),
                _clean(item_mod_data[columns_order.index("attributeIds")]).split(","),
                _clean(item_mod_data[columns_order.index("attributes")]).split(",")
                # ToDo: changeRangeModuleNames is missing
        ):
            if attr_val == "None":
                continue
            conn.execute(stmt, {
                "code": code,
                "typeCode": type_code,
                "changeType": change_type,
                "attributeOnly": attribute_only,
                "changeRange": change_range,
                "changeRangeModuleNameId": 0,
                "attributeId": attr_id,
                "attributeValue": attr_val,
            })
            i += 1
        return i

    def init_item_modifiers(self):
        logger.info("Initializing %s from %s and %s",
                    models.ItemModifiers.__tablename__,
                    models.ModifierDefinition.__tablename__,
                    models.ModifierValue.__tablename__)
        with self.engine.connect() as conn:
            logger.warning("Deleting contents from %s", models.ItemModifiers.__tablename__)
            stmt = delete(models.ItemModifiers)
            conn.execute(stmt)
            stmt = (
                select(
                    models.ModifierValue.code,
                    models.ModifierValue.attributes,
                    models.ModifierValue.typeName.label("typeCode"),
                    models.ModifierDefinition.changeTypes,
                    models.ModifierDefinition.attributeOnly,
                    models.ModifierDefinition.changeRanges,
                    models.ModifierDefinition.changeRangeModuleNames,
                    models.ModifierDefinition.attributeIds,
                ).select_from(
                    models.ModifierValue.__table__.join(
                        models.ModifierDefinition,
                        models.ModifierValue.typeName == models.ModifierDefinition.code,
                        isouter=True
                    )
                )
            )
            result = conn.execute(stmt)
            data = result.fetchall()
            logger.info("Collected %s data entries, inserting into %s", len(data), models.ItemModifiers.__tablename__)
            columns = []
            for col in result.keys():
                columns.append(col)
            count = 0
            i = 0
            num = len(data)
            for row in data:
                count += self.init_item_mod(row, columns, conn)
                i += 1
                if i % 100 == 0:
                    utils.print_loading_bar(i / num)
        logger.info("Inserted %s item modifiers into %s", count, models.ItemModifiers.__tablename__)

    def load_reprocess(self, file_path: str):
        logger.info("Loading reprocess data from %s", file_path)
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        raw = raw["data"]["item_baseartifice"]
        re_id = re.compile(r"item_id(\d)")
        re_num = re.compile(r"item_number(\d)")
        stmt = self.dialect.replace("reprocess", ["itemId", "resultId", "quantity"])
        with self.engine.connect() as conn:
            i = 0
            for item_id, data in raw.items():  # type: str, Dict[str, int]
                item_id = int(item_id)  # type: int
                reprocess_items = {}  # type: Dict[int, int]
                reprocess_values = {}
                for k, v in data.items():
                    match = re_id.match(k)
                    if match:
                        reprocess_items[int(match.group(1))] = v
                        continue
                    match = re_num.match(k)
                    if match:
                        reprocess_values[int(match.group(1))] = v
                for num, quantity in reprocess_values.items():
                    if quantity <= 0:
                        continue
                    result_id = reprocess_items[num]
                    conn.execute(stmt, {"itemId": item_id, "resultId": result_id, "quantity": quantity})
                    i += 1
            conn.commit()
        logger.info("Inserted %s rows into reprocess", i)

    def load_manufacturing(self, file_path: str):
        logger.info("Loading manufacturing data from %s", file_path)
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        raw = raw["data"]["item_manufacturing"]
        stmt_bp = self.dialect.upsert(
            "blueprints",
            ["blueprintId", "productId", "outputNum", "skillLvl", "materialAmendAtt", "decryptorMul", "money", "time",
             "timeAmendAtt", "type"])
        stmt_cost = self.dialect.upsert("blueprint_costs", ["blueprintId", "resourceId", "amount", "type"])
        b = 0
        c = 0
        species = {
            "module_species": "mod",
            "planetary_material_species": "pi",
            "minerals_species": "mins",
            "ship_species": "ship",
            "component_species": "comp",
            "blueprint_species": "bp",
            "datacore_species": "data",
            "salvage_material_species": "salv"
        }
        re_species = re.compile(r"[a-zA-z_]+_species")
        with self.engine.connect() as conn:
            for res_id, bp_data in raw.items():  # type: str, Dict[str, Any]
                res_id = int(res_id)  # type: int
                bp_id = int(bp_data["blueprint"])
                if res_id != int(bp_data["product_type_id"]):
                    raise DataException(
                        f"Blueprint for item {res_id} has wont product type: {int(bp_data['product_type_id'])}")
                conn.execute(stmt_bp, {
                    "blueprintId": bp_id,
                    "productId": res_id,
                    "outputNum": bp_data["output_num"],
                    "skillLvl": bp_data["skill_level"],
                    "materialAmendAtt": bp_data["material_amend_att"],
                    "decryptorMul": bp_data["decryptor_mul"],
                    "money": bp_data["money"],
                    "time": bp_data["time"],
                    "timeAmendAtt": bp_data["time_amend_att"],
                    "type": bp_data["type"]
                })
                b += 1
                for mat_id, quantity in bp_data["material"].items():  # type: str, int
                    mat_type = None
                    for k in bp_data:
                        if re_species.match(k):
                            if mat_id in bp_data[k]:
                                mat_type = species[k]
                    conn.execute(stmt_cost, {
                        "blueprintId": bp_id,
                        "resourceId": int(mat_id),
                        "amount": quantity,
                        "type": mat_type
                    })
                    c += 1
            conn.commit()
        logger.info("Inserted %s blueprints with %s costs into blueprints and blueprint_cost", b, c)
