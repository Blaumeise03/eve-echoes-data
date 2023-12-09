import importlib.util
import json
import logging
import os
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, DefaultDict, Union

from sqlalchemy import select, update
from sqlalchemy.orm import aliased

from echoes_data import utils, models
from echoes_data.extractor.basics import BasicLoader

logger = logging.getLogger("ee.extractor.universe")
NUMBER_TO_ROMA = [
    "", "I", "II", "III", "IV", "V",
    "VI", "VII", "VIII",
    "IX", "X",
    "XI", "XII", "XIII", "XIV",
    "XV",
    "XVI", "XVII", "XVIII",
    "XIX", "XX", "XXI",
    "XXII",
    "XXIII", "XXIV", "XXV",
    "XXVI", "XXVII",
    "XXVIII",
    "XXIX", "XXX"]


def get_item_types(path_item_type: str):
    spec = importlib.util.spec_from_file_location("eve.item_types", path_item_type)
    item_types = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item_types)
    category_ids = {}
    group_ids = {}
    type_ids = {}
    for cat in filter(lambda c: not c.startswith('__'), dir(item_types.CategoryIds)):
        category_ids[getattr(item_types.CategoryIds, cat)] = cat
    for group in filter(lambda g: not g.startswith('__'), dir(item_types.GroupIds)):
        group_ids[getattr(item_types.GroupIds, group)] = group
    for i_type in filter(lambda t: not t.startswith('__'), dir(item_types.ItemTypeIds)):
        type_ids[getattr(item_types.ItemTypeIds, i_type)] = i_type
    return category_ids, group_ids, type_ids


def get_item_types_legacy(python_path, script_path, path_script_dir: str):
    raw = subprocess.check_output([python_path, script_path, path_script_dir], shell=True, text=True)
    raw = json.loads(raw)
    raw = [dict([int(key), value]
                for key, value in dicts.items())
           for dicts in [raw["category_ids"], raw["group_ids"], raw["type_ids"]]]
    return raw[0], raw[1], raw[2]


class UniverseLoader:
    def __init__(self, db: BasicLoader):
        self.loader = db  # type: BasicLoader
        self.texts = {}  # type: Dict[int, str]
        self._cursor = None
        self.group_ids = {}  # type: Dict[int, Dict[str, Any]]
        self.named_group_ids = {}  # type: Dict[str, int]
        self.type_to_group_id = {}  # type: Dict[int, int]
        self.type_to_short_id = {}  # type: Dict[int, int]
        self.solar_systems = {}  # type: Dict[int, str]
        self.celestial_cache = {}  # type: Dict[int, Dict[str, Any]]
        self.python27_exe = None  # type: str | None

    def load_texts(self, file_path: Union[str, os.PathLike]):
        logger.info("Loading localized strings")
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        num = len(raw)
        logger.info("Translating %s strings", num)
        i = 0
        for k, v in raw.items():
            if "name" in v:
                self.texts[int(k)] = self.loader.get_localized_string(v["name"])
            i += 1
        logger.info("Loaded %s strings", i)

    def load_group_id_cache(self):
        logger.info("Loading group id cache")
        with self.loader.engine.connect() as conn:
            stmt = select(
                models.Group.id,
                models.Group.name,
                models.Group.localisedNameIndex,
                models.Group.sourceName
            )
            res = conn.execute(stmt).fetchall()
            for i, n, l_i, l_n in res:
                self.group_ids[i] = {
                    "name": n,
                    "loc_id": l_i,
                    "zh_name": l_n
                }
                self.named_group_ids[n] = i
            stmt = select(
                models.Type.id, models.Type.group_id
            )
            res = conn.execute(stmt).fetchall()
            for t, g in res:
                self.type_to_group_id[t] = g
            stmt = select(models.Type.id, models.Type.short_id).where(models.Type.short_id.is_not(None))
            res = conn.execute(stmt).fetchall()
            for i, s in res:
                self.type_to_short_id[i] = s

    def load_system_cache(self):
        logger.info("Loading solar system cache")
        stmt = select(models.Solarsystem.id, models.Solarsystem.name)
        with self.loader.engine.connect() as conn:
            res = conn.execute(stmt).fetchall()
            for i, n in res:
                self.solar_systems[i] = n

    def _save_get_group_name(self, group_id):
        # Reverse engineered from script/data_common/evetypes/__init__.py
        # script/data_common/static/item/item_data.py
        name = None
        if group_id in self.group_ids:
            zh_name = self.group_ids[group_id]["zh_name"]
            name = self.loader.get_localized_string(zh_name, return_def=False)
        if name is None:
            return str(group_id)

    def get_celestial_name(self, cel_id: int):
        # Reverse engineered from script/eveuniverse/universe.py
        celestial = self.celestial_cache[cel_id]
        celestial_index = celestial["celestial_index"] if "celestial_index" in celestial else 0
        orbit_index = celestial["orbit_index"] if "orbit_index" in celestial else None
        type_id = celestial["type_id"]
        group_id = self.type_to_group_id[type_id]
        if orbit_index:
            orbit_id = celestial["orbit_id"]
            if group_id in (self.named_group_ids["AsteroidBelt"], self.named_group_ids["Moon"]):
                return "{orbit} - {group} {orbit_index}".format(orbit=self.get_celestial_name(orbit_id),
                                                                group=self._save_get_group_name(group_id),
                                                                orbit_index=orbit_index)
        else:
            solar_system_id = celestial["solar_system_id"]
            # This was changed, not sure how it originally worked with suns
            # Their ingame name is something lik 'Sun K7 (Orange)' but I'm to lazy to do it properly
            if group_id == self.named_group_ids["Sun"]:
                return f"Sun {celestial['statistics']['spectral_class']}"
            return "{sol} {cel_index}".format(
                sol=self.solar_systems[solar_system_id],
                cel_index=NUMBER_TO_ROMA[celestial_index])

    def load_item_types(self,
                        path_item_type: Optional[Union[str, os.PathLike]] = None,
                        path_script: Optional[Union[str, os.PathLike]] = None,
                        path_item_types_by_group: Optional[Union[str, os.PathLike]] = None,
                        path_type_id_mapping: Optional[Union[str, os.PathLike]] = None):
        # Reversed engineered from
        # script/data_common/static/item/item_type for long Type and Group IDs
        if path_item_type is None and path_script is None:
            raise TypeError("Expected at least one argument of path_item_type and path_script")
        if path_item_type is not None:
            category_ids, group_ids, type_ids = get_item_types(path_item_type)
        else:
            category_ids, group_ids, type_ids = get_item_types_legacy(
                self.python27_exe, Path("legacy_adapter/extract_pyc.py"),
                path_script)

        type_groups = defaultdict(lambda: None)  # type: DefaultDict[int, Optional[int]]
        type_shorts = defaultdict(lambda: None)  # type: DefaultDict[int, Optional[int]]
        if path_item_types_by_group is not None:
            with open(path_item_types_by_group, "r", encoding="utf-8") as file:
                raw = json.load(file)
            for g, ids in raw.items():  # type: str, List[int]
                for i in ids:
                    type_groups[i] = int(g)
            logger.info("Loaded %s item_type-group relations", len(type_groups))
        if path_type_id_mapping is not None:
            with open(path_type_id_mapping, "r", encoding="utf-8") as file:
                raw = json.load(file)
            for s, t in raw["data"]["type_id"].items():  # type: str, int
                type_shorts[t] = int(s)
            logger.info("Loaded %s short item_type ids", len(type_ids))

        logger.info("Loaded %s category ids, %s group ids and %s type ids",
                    len(category_ids), len(group_ids), len(type_ids))

        with self.loader.engine.connect() as conn:
            stmt = self.loader.dialect.upsert("categories", ["id", "name"])
            conn.execute(stmt, list(map(lambda t: {"id": t[0], "name": t[1]}, category_ids.items())))
            stmt = self.loader.dialect.upsert("groups", ["id", "name"])
            conn.execute(stmt, list(map(lambda t: {"id": t[0], "name": t[1]}, group_ids.items())))
            stmt = self.loader.dialect.upsert("types", ["id", "name", "group_id", "short_id"])
            for i, n in type_ids.items():
                # Batch doesn't work for this one
                conn.execute(stmt, {
                    "id": i, "group_id": type_groups[i], "short_id": type_shorts[i], "name": n
                })
            conn.commit()
        logger.info("Inserted %s category ids, %s group ids and %s type ids",
                    len(category_ids), len(group_ids), len(type_ids))

    def load_data(self,
                  file_path: Union[str, os.PathLike],
                  table: str,
                  columns: List[str],
                  direct_name=False,
                  loading_bar=False,
                  name_func: Optional[Callable[[int], None]] = None,
                  cache_celestials=False,
                  return_raw=False):

        logger.info("Loading data from %s into %s", file_path, table)
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        num = len(raw)
        if loading_bar:
            utils.activate_loading_bar(num, info=file_path)
        if cache_celestials:
            logger.info("Caching %s celestials", num)
            i = 0
            for k, v in raw.items():
                self.celestial_cache[int(k)] = v
                if loading_bar and i % 10000 == 0:
                    utils.print_loading_bar(i)
                i += 1
        if loading_bar:
            utils.activate_loading_bar(num, f"Inserting into table {table}")
            logger.info("Inserting %s entries into %s", num, table)
        stmt = self.loader.dialect.upsert(table, list(map(lambda a: a if type(a) != tuple else a[0], columns)))
        overflow_items = []
        with self.loader.engine.connect() as conn:
            not_found = []
            i = 0
            for i_id, item in raw.items():
                i_id = int(i_id)
                if name_func is not None:
                    i_name = name_func(i_id)
                elif not direct_name:
                    if i_id in self.texts:
                        i_name = self.texts[i_id]
                    else:
                        i_name = None
                else:
                    i_name = item["name"]
                data = {}
                if i_name is None:
                    pass  # continue
                for col in columns:
                    key = col
                    if type(col) == tuple:
                        key = col[1]
                        col = col[0]
                    if callable(key):
                        # noinspection PyCallingNonCallable
                        data[col] = key(item)
                    elif key == "id":
                        data[col] = i_id
                    elif key == "name":
                        data[col] = i_name
                    elif key in "xyz":
                        if "position" in item:
                            # Celestials
                            data[col] = (item["position"][key])
                        elif "center" in item:
                            # Regions, Constellations and Systems
                            data[col] = (item["center"][key])
                        else:
                            # Stars
                            data[col] = 0
                    elif key in item:
                        data[col] = (item[key])
                    else:
                        data[col] = None
                        if key not in not_found:
                            not_found.append(key)
                for k, val in data.items():
                    if not type(val) == int and not type(val) == float:
                        continue
                    val = int(val)
                    if val.bit_length() > 63:
                        overflow_items.append(i_id)
                        data[k] = None
                conn.execute(stmt, data)
                if loading_bar and i % 1000 == 0:
                    utils.print_loading_bar(i)
                i += 1
            conn.commit()
        if loading_bar:
            utils.clear_loading_bar()
        if len(not_found) > 0:
            logger.warning("Did not find these keys in file %s: %s", file_path, not_found)
        if len(overflow_items) > 0:
            logger.warning("%s data entries were exceeding the 64bit limit, the values were replaced with NULL for %s",
                           len(overflow_items), table)
        logger.info("Inserted %s entries into %s", len(raw), table)
        if return_raw:
            return raw

    def init_system_neighbours(self, systems: Dict[str, Any]):
        with self.loader.engine.connect() as conn:
            stmt = self.loader.dialect.replace("system_connections", ["originId", "destinationId"])
            for sys_id, system in systems.items():
                sys_id = int(sys_id)
                for n_id in system["neighbours"]:
                    conn.execute(stmt, {"originId": sys_id, "destinationId": n_id})
                stmt = update(models.Constellation).values(region_id=system["region_id"]).where(
                    id=system["constellation_id"])
                conn.execute(stmt)
            conn.commit()

    def load_stargates_connections(self, stargates: Dict[str, Any]):
        with self.loader.engine.connect() as conn:
            stmt = self.loader.dialect.replace("stargates", ["from_gate_id", "from_sys_id", "to_gate_id", "to_sys_id"])
            for from_id, stargate in stargates.items():
                from_id = int(from_id)
                conn.execute(stmt, {
                    "from_gate_id": from_id,
                    "from_sys_id": stargate["from_solar_system_id"],
                    "to_gate_id": stargate["to_stargate_id"],
                    "to_sys_id": stargate["to_solar_system_id"]
                })
            conn.commit()
            logger.info("Inserted %s stargate connections into database", len(stargates))

    def init_cobalt_edge(self):
        sys_from = aliased(models.Solarsystem)
        sys_to = aliased(models.Solarsystem)
        stmt = (
            select(
                sys_from.id.label("from_id"),
                sys_to.id.label("to_id"),
            )
            .join(sys_from.region)
            .join(models.StargateConnections, models.StargateConnections.c.from_sys_id == sys_from.id)
            .join(sys_to, sys_to.id == models.StargateConnections.c.to_sys_id)
            .where(models.Region.name == "Cobalt Edge")
        )
        with self.loader.engine.connect() as conn:
            connections = conn.execute(stmt).fetchall()
            stmt = self.loader.dialect.upsert("system_connections", ["originId", "destinationId"])
            for sys_from_id, sys_to_id in connections:
                conn.execute(stmt, {
                    "originId": sys_from_id,
                    "destinationId": sys_to_id
                })
            logger.info("Inserted %s system connections for region Cobalt Edge", len(connections))
            conn.commit()

    def load_planetary_production(self, file_path: Union[str, os.PathLike]):
        logger.info("Loading planetary production data from %s", file_path)
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        num = len(raw)
        logger.info("Loaded %s planets, inserting into database", num)
        utils.activate_loading_bar(num)
        i = 0
        j = 0
        stmt = self.loader.dialect.replace(
            "planet_exploit",
            ["planet_id", "type_id", "output", "richness", "richness_value", "location_index"])
        richness = ['poor', 'medium', 'rich', 'perfect']
        with self.loader.engine.connect() as conn:
            for planet in raw.values():  # type: Dict[str, Any]
                p_id = planet["planet_id"]
                for res in planet["resource_info"].values():  # type: Dict[str, Union[int, float]]
                    rich_i = res["richness_index"]
                    conn.execute(
                        stmt,
                        {
                            "planet_id": p_id,
                            "type_id": res["resource_type_id"],
                            "output": res["init_output"],
                            "richness": richness[rich_i - 1],
                            "richness_value": res["richness_value"],
                            "location_index": res["location_index"]
                        })
                    j += 1
                if i % 100 == 0:
                    utils.print_loading_bar(i)
                i += 1
        utils.clear_loading_bar()
        logger.info("Inserted %s resources from %s planets into the database", j, num)
