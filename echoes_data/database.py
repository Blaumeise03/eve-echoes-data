import functools
import json
import logging
import os
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from sqlite3 import Error, Connection, Cursor
from typing import Dict, Any, Tuple, Type, Optional, List, Union, Callable

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


class EchoesDB:
    def __init__(self) -> None:
        self.strings_en = {}  # type: Dict[int, str]
        self.conn = None  # type: Connection | None
        self.strings = {}  # type: Dict[str, int]
        self.new_loc_cache = {}

    def create_connection(self, db_file: str):
        """ create a database connection to a SQLite database """
        try:
            self.conn = sqlite3.connect(db_file)
        except Error as e:
            logger.error("Error while opening database", exc_info=e)

    def _insert_data(self, table: str, data: Dict[str, Any], cursor: Cursor):
        placeholders = ', '.join(['?'] * len(data))
        columns = ', '.join(data.keys())
        sql = "REPLACE INTO %s ( %s ) VALUES ( %s )" % (table, columns, placeholders)
        cursor.execute(sql, list(data.values()))

    @context_cursor
    def load_dict_data(self,
                       cursor: Cursor,
                       file: str,
                       table: str,
                       merge_with_file: Optional[str] = None,
                       auto_schema=True,
                       schema: Optional[Dict[str, Tuple[str, Type]]] = None,
                       fields: Optional[str] = None,
                       default_values: Optional[Dict[str, Any]] = None,
                       localized: Optional[Dict[str, str]] = None,
                       dict_root_key: Optional[str] = None):
        logger.info("Loading data from file %s into %s", file, table)
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
        # iterate all items in file
        for item_id, item in raw.items():
            data = {schema["key"][0]: schema["key"][1](item_id)}
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
                        data[field] = -2
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
            self._insert_data(table, data, cursor)
            loaded += 1
        self.conn.commit()
        logger.info("Loaded %s rows into table %s from file %s", loaded, table, file)
        self.save_localized_cache()

    def load_all_dict_data(self,
                           root_path: str,
                           table: str,
                           regex: Optional[re.Pattern] = None,
                           merge_with_file_path: Optional[str] = None,
                           auto_schema=True,
                           schema: Optional[Dict[str, Tuple[str, Type]]] = None,
                           fields: Optional[str] = None,
                           default_values: Optional[Dict[str, Any]] = None,
                           localized: Optional[Dict[str, str]] = None):
        directory = os.fsencode(root_path)
        logger.info("Loading data from dir %s into %s", root_path, table)
        count = 0
        if regex is None:
            regex = re.compile(r"\d+\.json")
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if not re.match(regex, filename):
                continue
            file_2 = None
            if merge_with_file_path and os.path.exists(f"{merge_with_file_path}/{filename}"):
                file_2 = f"{merge_with_file_path}/{filename}"
            self.load_dict_data(
                file=f"{root_path}/{filename}", table=table, merge_with_file=file_2, auto_schema=auto_schema,
                schema=schema, fields=fields, default_values=default_values, localized=localized
            )
            count += 1
        logger.info("Loaded %s files into %s from %s", count, table, root_path)

    @context_cursor
    def _insert_batch_data(self, cursor: Cursor, table: str, key_field: str, value_field: str, batch: List[Tuple[Any, Any, Any]]):
        sql = "INSERT INTO %s ( %s, %s ) VALUES ( ?, ? ) ON CONFLICT( %s ) DO UPDATE SET %s=?" % (
            table, key_field, value_field, key_field, value_field)
        cursor.executemany(sql, batch)

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
            batch.append((key_type(key), value_type(value), value_type(value)))
            if save_lang:
                self.strings[value_type(value)] = key_type(key)
        self._insert_batch_data(table, key_field, value_field, batch)
        if logging:
            logger.info("Inserted %s rows from %s : %s into %s", len(batch), file, root_key, table)
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

    @context_cursor
    def get_next_loc_id(self, cursor):
        start = 5000000000
        cursor.execute("SELECT id FROM localised_strings WHERE id>=? ORDER BY ID DESC LIMIT 1;", (start,))
        res = cursor.fetchone()
        if res is not None:
            start = res[0] + 1
        return start

    @context_cursor
    def get_localized_id(self, cursor: Cursor, zh_name: str, save_new=False, only_cache=True) -> int:
        if zh_name in self.strings:
            return self.strings[zh_name]
        res = None
        if not only_cache:
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

    def get_localized_string(self, zh_name: str, return_def=True):
        # cursor = self.conn.cursor()
        # cursor.execute("SELECT en FROM localised_strings WHERE source=?;", (zh_name,))
        # res = cursor.fetchone()
        # if res is None:
        #     return None
        # return res[0]
        if zh_name not in self.strings:
            if return_def:
                return zh_name
            return None
        return self.strings_en[self.strings[zh_name]]

    @context_cursor
    def load_localized_cache(self, cursor):
        cursor.execute("SELECT id, source, en FROM localised_strings")
        res = cursor.fetchall()
        for s_id, source, en in res:
            self.strings[source] = s_id
            self.strings_en[s_id] = en
        logger.info("Loaded %s localized strings into the cache", len(res))

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

    @context_cursor
    def load_item_attributes(self, cursor, file: str, table: str, columns: Tuple[str, str, str]):
        with open(file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        batch = []
        for item_id, attrs in raw.items():
            for attr, value in attrs.items():
                batch.append((int(item_id), int(attr), value, value))
        sql = f"INSERT INTO {table} ( {columns[0]}, {columns[1]}, {columns[2]} ) VALUES ( ?, ?, ? ) ON CONFLICT DO UPDATE SET {columns[2]}=?"
        cursor.executemany(sql, batch)
        self.conn.commit()
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
        self.conn.commit()
        logger.info("Saved %s files from %s into %s", count, root_path, table)

    def init_item_mod(self, table: str, item_mod_data: List[Union[str, Any]], columns_order: List[str], cursor: Cursor):
        def _clean(string: str) -> str:
            return string.rstrip("[").lstrip("]").replace("\"", "").replace(" ", "")

        sql = (f"INSERT INTO {table} ( "
               "    code, typeCode, changeType, attributeOnly, "
               "    changeRange, changeRangeModuleNameId, attributeId, attributeValue"
               ") VALUES ( ?, ?, ?, ?, ?, ?, ?, ? ) "
               "ON CONFLICT DO UPDATE SET "
               "    typeCode=?, changeType=?, attributeOnly=?, "
               "    changeRange=?, changeRangeModuleNameId=?, attributeId=?, attributeValue=?")
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
            cursor.execute(sql, (
                code, type_code, change_type, attribute_only, change_range, 0, attr_id, attr_val,
                type_code, change_type, attribute_only, change_range, 0, attr_id, attr_val
            ))
            i += 1
        return i

    @context_cursor
    def init_item_modifiers(self, cursor,
                            table: str = "item_modifiers",
                            table_def: str = "modifier_definition",
                            table_val: str = "modifier_value"):
        logger.info("Initializing %s from %s and %s", table, table_def, table_val)
        logger.warning("Deleting contents from %s", table)
        # noinspection SqlWithoutWhere
        cursor.execute(f"DELETE FROM {table}")
        cursor.execute("SELECT"
                       "    mv.code, mv.attributes, mv.typeName as typeCode,"
                       "    md.changeTypes, md.attributeOnly, md.changeRanges, md.changeRangeModuleNames, md.attributeIds "
                       f"FROM {table_val} mv "
                       f"LEFT JOIN {table_def} md on mv.typeName = md.code;")
        data = cursor.fetchall()
        logger.info("Collected %s data entries, inserting into %s", len(data), table)
        columns = []
        for col in cursor.description:
            columns.append(col[0])
        count = 0
        for row in data:
            count += self.init_item_mod(table, row, columns, cursor)
        logger.info("Inserted %s item modifiers into %s", count, table)

    @context_cursor
    def load_reprocess(self, cursor, file_path: str):
        logger.info("Loading reprocess data from %s", file_path)
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        raw = raw["data"]["item_baseartifice"]
        re_id = re.compile(r"item_id(\d)")
        re_num = re.compile(r"item_number(\d)")
        sql = "INSERT OR REPLACE INTO reprocess (itemId, resultId, quantity) VALUES ( ?, ?, ?)"
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
                cursor.execute(sql, (item_id, result_id, quantity))
                i += 1
        self.conn.commit()
        logger.info("Inserted %s rows into reprocess", i)

    @context_cursor
    def load_manufacturing(self, cursor, file_path: str):
        logger.info("Loading manufacturing data from %s", file_path)
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        raw = raw["data"]["item_manufacturing"]
        sql_bp = ("INSERT OR REPLACE INTO blueprints "
                  " (blueprintId, productId, outputNum, skillLvl, materialAmendAtt, decryptorMul, money, time, timeAmendAtt, type) "
                  " VALUES ( ?,?,?,?,?,?,?,?,?,?)")
        sql_cost = "INSERT OR REPLACE INTO blueprint_costs (blueprintId, resourceId, amount, type) VALUES (?,?,?,?)"
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
        for res_id, bp_data in raw.items():  # type: str, Dict[str, Any]
            res_id = int(res_id)  # type: int
            bp_id = int(bp_data["blueprint"])
            if res_id != int(bp_data["product_type_id"]):
                raise DataException(
                    f"Blueprint for item {res_id} has wront product type: {int(bp_data['product_type_id'])}")
            cursor.execute(sql_bp, (
                bp_id,
                res_id,
                bp_data["output_num"],
                bp_data["skill_level"],
                bp_data["material_amend_att"],
                bp_data["decryptor_mul"],
                bp_data["money"],
                bp_data["time"],
                bp_data["time_amend_att"],
                bp_data["type"]
            ))
            b += 1
            for mat_id, quantity in bp_data["material"].items():  # type: str, int
                mat_type = None
                for k in bp_data:
                    if re_species.match(k):
                        if mat_id in bp_data[k]:
                            mat_type = species[k]
                cursor.execute(sql_cost, (bp_id, int(mat_id), quantity, mat_type))
                c += 1
        self.conn.commit()
        logger.info("Inserted %s blueprints with %s costs into blueprints and blueprint_cost", b, c)
