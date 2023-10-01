import importlib.util
import json
import logging
from collections import defaultdict
from sqlite3 import Cursor
from typing import Dict, List, Any, Optional, Callable, DefaultDict, Union

from echoes_data import utils
from echoes_data.database import EchoesDB

logger = logging.getLogger("ee.universe")
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


def add_solarsystem_neighbours(cursor: Cursor, system_id: int, system: Dict[str, Any]):
    sql = "INSERT OR REPLACE INTO system_connections (origin_id, destination_id) VALUES (?, ?)"
    for n_id in system["neighbours"]:
        cursor.execute(sql, (system_id, n_id))
    sql = "UPDATE constellations SET region_id=? WHERE id=?"
    cursor.execute(sql, (system["region_id"], system["constellation_id"]))


class UniverseLoader:
    def __init__(self, db: EchoesDB):
        self.db = db  # type: EchoesDB
        self.texts = {}  # type: Dict[int, str]
        self._cursor = None
        self.group_ids = {}  # type: Dict[int, Dict[str, Any]]
        self.named_group_ids = {}  # type: Dict[str, int]
        self.type_to_group_id = {}  # type: Dict[int, int]
        self.type_to_short_id = {}  # type: Dict[int, int]
        self.solar_systems = {}  # type: Dict[int, str]
        self.celestial_cache = {}  # type: Dict[int, Dict[str, Any]]

    def cursor(self):
        if self._cursor is None:
            self._cursor = self.db.conn.cursor()
        return self._cursor

    def load_texts(self, file_path: str):
        logger.info("Loading localized strings")
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        num = len(raw)
        logger.info("Translating %s strings", num)
        i = 0
        for k, v in raw.items():
            if "name" in v:
                self.texts[int(k)] = self.db.get_localized_string(v["name"])
            i += 1
        logger.info("Loaded %s strings", i)

    def load_group_id_cache(self):
        logger.info("Loading group id cache")
        sql = "SELECT id, name, localisedNameIndex, sourceName FROM groups"
        cursor = self.cursor()
        cursor.execute(sql)
        res = cursor.fetchall()
        for i, n, l_i, l_n in res:
            self.group_ids[i] = {
                "name": n,
                "loc_id": l_i,
                "zh_name": l_n
            }
            self.named_group_ids[n] = i
        sql = "SELECT id, group_id FROM types"
        cursor.execute(sql)
        res = cursor.fetchall()
        for t, g in res:
            self.type_to_group_id[t] = g
        sql = "SELECT id, short_id FROM types WHERE short_id IS NOT NULL"
        cursor.execute(sql)
        res = cursor.fetchall()
        for i, s in res:
            self.type_to_short_id[i] = s

    def load_system_cache(self):
        logger.info("Loading solar system cache")
        sql = "SELECT id, name FROM solarsystems"
        cursor = self.cursor()
        cursor.execute(sql)
        res = cursor.fetchall()
        for i, n in res:
            self.solar_systems[i] = n

    def _save_get_group_name(self, group_id):
        # Reverse engineered from script/data_common/evetypes/__init__.py
        # script/data_common/static/item/item_data.py
        name = None
        if group_id in self.group_ids:
            zh_name = self.group_ids[group_id]["zh_name"]
            name = self.db.get_localized_string(zh_name, return_def=False)
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
                        path_item_type: str,
                        path_item_types_by_group: Optional[str] = None,
                        path_type_id_mapping: Optional[str] = None):
        # Reversed engineered from
        # script/data_common/static/item/item_type for long Type and Group IDs
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
        sql = "INSERT INTO %s ( id, name ) VALUES ( ?, ? ) ON CONFLICT DO UPDATE SET name=?"
        for i, n in category_ids.items():
            self.cursor().execute(sql % "categories", (i, n, n))
        for i, n in group_ids.items():
            self.cursor().execute(sql % "groups", (i, n, n))
        sql = ("INSERT INTO types ( id, name, group_id, short_id ) "
               "    VALUES ( ?, ?, ?, ? ) ON CONFLICT DO UPDATE "
               "    SET name=?, group_id=?, short_id=?")
        for i, n in type_ids.items():
            g = str(type_groups[i])
            s = str(type_shorts[i])
            self.cursor().execute(sql, (i, n, g, s, n, g, s))
        self.db.conn.commit()
        logger.info("Inserted %s category ids, %s group ids and %s type ids",
                    len(category_ids), len(group_ids), len(type_ids))

    def load_data(self,
                  file_path: str,
                  table: str,
                  columns: List[str],
                  extra_task: Optional[Callable[[Cursor, int, Dict[str, Any]], None]] = None,
                  direct_name=False,
                  loading_bar=False,
                  name_func: Optional[Callable[[int], None]] = None,
                  cache_celestials=False):

        logger.info("Loading data from %s into %s", file_path, table)
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        num = len(raw)
        if cache_celestials:
            logger.info("Caching %s celestials", num)
            i = 0
            if loading_bar:
                utils.print_loading_bar(i / num)
            for k, v in raw.items():
                self.celestial_cache[int(k)] = v
                if loading_bar and i % 10000 == 0:
                    utils.print_loading_bar(i / num)
                i += 1
        if loading_bar:
            logger.info("Inserting %s entries into %s", num, table)
        col_names = ", ".join(map(lambda s: s if type(s) == str else s[0], columns))
        sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({','.join(['?'] * len(columns))})"
        not_found = []
        i = 0
        for i_id, item in raw.items():
            i_id = int(i_id)
            if name_func is not None:
                i_name = name_func(i_id)
            elif not direct_name:
                i_name = self.texts[i_id]
            else:
                i_name = item["name"]
            data = []
            if i_name is None:
                continue
            for col in columns:
                key = col
                if type(col) == tuple:
                    key = col[1]
                    col = col[0]
                if callable(key):
                    # noinspection PyCallingNonCallable
                    data.append(key(item))
                elif key == "id":
                    data.append(i_id)
                elif key == "name":
                    data.append(i_name)
                elif key in "xyz":
                    if "position" in item:
                        # Celestials
                        data.append(item["position"][key])
                    elif "center" in item:
                        # Regions, Constellations and Systems
                        data.append(item["center"][key])
                    else:
                        # Stars
                        data.append(0)
                elif key in item:
                    data.append(item[key])
                else:
                    data.append(None)
                    if key not in not_found:
                        not_found.append(key)
            self.cursor().execute(sql, data)
            if extra_task is not None:
                extra_task(self.cursor(), i_id, item)
            if loading_bar and i % 1000 == 0:
                utils.print_loading_bar(i / num)
            i += 1
        self.db.conn.commit()
        if len(not_found) > 0:
            logger.warning("Did not find these keys in file %s: %s", file_path, not_found)
        logger.info("Inserted %s entries into %s", len(raw), table)

    def load_planetary_production(self, file_path: str):
        logger.info("Loading planetary production data from %s", file_path)
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        curser = self.cursor()
        num = len(raw)
        logger.info("Loaded %s planets, inserting into database", num)
        utils.print_loading_bar(0)
        i = 0
        j = 0
        sql = ("INSERT OR REPLACE INTO planet_exploit "
               "    (planet_id, type_id, output, richness, richness_value, location_index) "
               "    VALUES ( ?, ?, ?, ?, ?, ?)")
        RICHNESS = ['poor', 'medium', 'rich', 'perfect']
        for planet in raw.values():  # type: Dict[str, Any]
            p_id = planet["planet_id"]
            for res in planet["resource_info"].values():  # type: Dict[str, Union[int, float]]
                rich_i = res["richness_index"]
                curser.execute(
                    sql,
                    (p_id, res["resource_type_id"], res["init_output"], RICHNESS[rich_i - 1],
                     res["richness_value"], res["location_index"]))
                j += 1
            if i % 1000 == 0:
                utils.print_loading_bar(i / num)
            i += 1
        self.db.conn.commit()
        logger.info("Inserted %s resources from %s planets into the database", j, num)

    def setup_tables(self):
        logger.info("Creating universe tables")
        self.db.conn.execute("create table if not exists regions ("
                             "    id         int    not null primary key,"
                             "    name       TEXT   not null,"
                             "    x          bigint null,"
                             "    y          bigint null,"
                             "    z          bigint null,"
                             "    faction_id int    null,"
                             "    radius     bigint null,"
                             "    wormhole_class_id int null"
                             ")")
        self.db.conn.execute("create table if not exists constellations("
                             "    id                int    not null primary key,"
                             "    region_id         int    null,"
                             "    name              TEXT   not null,"
                             "    x                 bigint null,"
                             "    y                 bigint null,"
                             "    z                 bigint null,"
                             "    faction_id        int    null,"
                             "    radius            bigint null,"
                             "    wormhole_class_id int    null,"
                             "    constraint key_const_reg"
                             "        foreign key (region_id) references regions (id)"
                             "            on delete cascade"
                             ")")
        self.db.conn.execute("create table if not exists solarsystems("
                             "    id               int    not null primary key,"
                             "    region_id        int    null,"
                             "    constellation_id int    null,"
                             "    name             TEXT   not null,"
                             "    x                bigint null,"
                             "    y                bigint null,"
                             "    z                bigint null,"
                             "    security         float  null,"
                             "    faction_id       int    null,"
                             "    radius           bigint null,"
                             "    constraint key_sys_const"
                             "        foreign key (constellation_id) references constellations (id)"
                             "            on delete cascade,"
                             "    constraint key_sys_reg"
                             "        foreign key (region_id) references regions (id))")

        self.db.conn.execute("create index if not exists ix_solarsystem_name"
                             "    on solarsystems (name);")

        self.db.conn.execute("create table if not exists system_connections("
                             "    origin_id      int not null,"
                             "    destination_id int not null,"
                             "    PRIMARY KEY (origin_id, destination_id), "
                             "    constraint key_sys_const"
                             "        foreign key (origin_id) references solarsystems (id)"
                             "            on delete cascade,"
                             "    constraint key_sys_const"
                             "       foreign key (destination_id) references solarsystems (id)"
                             "            on delete cascade)")
        self.db.conn.execute("create table if not exists celestials("
                             "    id              int auto_increment primary key,"
                             "    name            TEXT   not null,"
                             "    type_id         int    null,"
                             "    group_id        int    null,"
                             "    system_id       int    null,"
                             "    orbit_id        int    null,"
                             "    x               bigint null,"
                             "    y               bigint null,"
                             "    z               bigint null,"
                             "    radius          bigint null,"
                             "    security        float  null,"
                             "    celestial_index int    null,"
                             "    orbit_index     int    null,"
                             "    constraint key_celest_sys"
                             "        foreign key (system_id) references solarsystems (id)"
                             "            on delete cascade,"
                             "    constraint key_celest_celest"
                             "        foreign key (orbit_id) references celestials (id)"
                             "            on delete cascade)")
        self.db.conn.execute("create table if not exists planet_exploit("
                             "    planet_id      int    not null,"
                             "    type_id        bigint not null,"
                             "    output         float  not null,"
                             "    richness       text  CHECK(richness in ('poor', 'medium', 'rich', 'perfect')) not null,"
                             "    richness_value int    not null,"
                             "    location_index int    not null,"
                             "    primary key (planet_id, type_id),"
                             "    constraint key_planex_item"
                             "        foreign key (type_id) references items (id),"
                             "    constraint key_planex_planet"
                             "        foreign key (planet_id) references celestials (id)"
                             "            on delete cascade)")
