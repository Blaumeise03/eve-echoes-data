import functools
import json
import logging
import os.path
import re
from pathlib import Path
from typing import List, Union, Callable, Tuple, Optional

from echoes_data import models
from echoes_data.database import EchoesDB
from echoes_data.extractor import basics, universe

logger = logging.getLogger("ee.extractor")


class PathLibrary:
    def __init__(self, root_path: Path):
        if type(root_path) == str:
            root_path = Path(root_path)
        elif not isinstance(root_path, Path):
            root_path = Path(root_path)
        self.root_path = root_path

    def verify_files(self) -> List[Tuple[str, Path]]:
        missing = []  # type: List[Tuple[str, Path]]
        for key in filter(lambda k: k.startswith("path_"), dir(self)):
            path = getattr(self, key)
            if not os.path.exists(path):
                missing.append((key, path))
        return missing

    def get_file_list(self) -> List[Tuple[str, Path]]:
        res = [(key, getattr(self, key)) for key in filter(lambda k: k.startswith("path_"), dir(self))]
        res.sort(key=lambda t: t[1])
        return res

    @property
    def path_gettext(self):
        return self.root_path / "staticdata" / "gettext"

    @property
    def path_group(self):
        return self.root_path / "staticdata" / "items" / "group.json"

    @property
    def path_category(self):
        return self.root_path / "staticdata" / "items" / "category.json"

    @property
    def path_script(self):
        return self.root_path / "script"

    @property
    def path_item_type(self):
        return self.root_path / "script" / "data_common" / "static" / "item" / "item_type.py"

    @property
    def path_item_types_by_group(self):
        return self.root_path / "staticdata" / "items" / "item_types_by_group.json"

    @property
    def path_type_id_mapping(self):
        return self.root_path / "py_data" / "data_common" / "static" / "item" / "type_id_mapping.json"

    @property
    def path_market_sell(self):
        """
        Contains all market groups with names and relations (items not included)
        """
        return self.root_path / "py_data" / "data_common" / "static" / "market_sell_items.json"

    @property
    def path_market_sell2(self):
        """
        Contains the items mapped to their market group, as well as the default item price (not estimated prices!)
        """
        return self.root_path / "py_data" / "data_common" / "static" / "market_sell_items_2.json"

    @property
    def path_units(self):
        return self.root_path / "staticdata" / "dogma" / "units.json"

    @property
    def path_attributes(self):
        return self.root_path / "staticdata" / "dogma" / "attributes.json"

    @property
    def path_effects(self):
        return self.root_path / "staticdata" / "dogma" / "effects.json"

    @property
    def path_items_root(self):
        return self.root_path / "staticdata" / "items"

    @property
    def path_items_dogma_root(self):
        return self.root_path / "staticdata" / "items" / "item_dogma"

    @property
    def path_item_nanocore(self):
        return self.root_path / "staticdata" / "items" / "item_nanocore.json"

    @property
    def path_item_skill(self):
        """
        Contains data for skill-chips
        """
        return self.root_path / "staticdata" / "items" / "item_skill.json"

    @property
    def path_item_drop(self):
        """
        Contains data for skill-chips
        """
        return self.root_path / "staticdata" / "items" / "item_skill.json"

    @property
    def path_repackage(self):
        return self.root_path / "py_data" / "data_common" / "static" / "item" / "repackage_volume.json"

    @property
    def path_reprocess(self):
        return self.root_path / "py_data" / "data_common" / "static" / "reprocess.json"

    @property
    def path_industry(self):
        return self.root_path / "py_data" / "data_common" / "static" / "spacestation" / "industry.json"

    @property
    def path_dogma_root(self):
        return self.root_path / "staticdata" / "dogma"

    @property
    def path_cal_codes_mod(self):
        return self.root_path / "py_data" / "data_common" / "static" / "dogma" / "cal_code_modifier.json"

    @property
    def path_type_effects(self):
        return self.root_path / "staticdata" / "dogma" / "type_effects.json"

    @property
    def path_universe_text(self):
        return self.root_path / "sigmadata" / "eve" / "universe" / "gettext.json"

    @property
    def path_constellations(self):
        return self.root_path / "sigmadata" / "eve" / "universe" / "constellations.json"

    @property
    def path_solar_systems(self):
        return self.root_path / "sigmadata" / "eve" / "universe" / "solar_systems.json"

    @property
    def path_stars(self):
        return self.root_path / "sigmadata" / "eve" / "universe" / "stars.json"

    @property
    def path_celestials(self):
        return self.root_path / "sigmadata" / "eve" / "universe" / "celestials.json"

    @property
    def path_stargates(self):
        return self.root_path / "sigmadata" / "eve" / "universe" / "stargates.json"

    @property
    def path_planet_exploit(self):
        return self.root_path / "manual_staticdata" / "universe" / "planet_exploit_resource.json"

    @property
    def path_corp_tech(self):
        return self.root_path / "py_data" / "data_common" / "static" / "corp_tech_skill.json"

    @property
    def path_tips_attr(self):
        return self.root_path / "py_data" / "data_common" / "static" / "tips_attrs.json"


class BaseExtractor:
    _extractors = []  # type: List[BaseExtractor.Extractor]

    class Extractor:
        def __init__(self, name: str, func: Callable[["EchoesExtractor"], None], requires: List[str]):
            self.func = func
            self.name = name
            self.requires = requires

        def check_requirements(self, loaded: List[str], wanted: List[str]):
            # 0 = all requirements met
            # 1 = missing reqs, but those will never be loaded
            # 2 = missing reqs that will be loaded
            state = 0
            for req in self.requires:
                if state <= 1 and req in wanted:
                    state = 1
                    if req not in loaded:
                        state = 2
            return state

    @classmethod
    def get_all_scopes(cls) -> List[str]:
        res = []
        for extr in cls._extractors:
            res.append(extr.name)
        return res

    @staticmethod
    def find_order(scopes: List[str]):
        wanted = []
        for extr in BaseExtractor._extractors:
            if extr.name in scopes:
                wanted.append(extr)
            elif extr.name == "lang_cache":
                wanted.append(extr)
        order = []  # type: List[BaseExtractor.Extractor]
        available = list(map(lambda e: e.name, wanted))  # type: List[str]
        loaded = []  # type: List[str]
        while len(wanted) > 0:
            wanted.sort(key=lambda e: e.check_requirements(loaded, available))
            next_extr = wanted.pop(0)
            loaded.append(next_extr.name)
            order.append(next_extr)
        return order

    @classmethod
    def extractor(cls, name: str, requires: Union[List[str], str, None] = None):
        if requires is None:
            requires = []
        elif type(requires) == str:
            requires = [requires]

        def decorator(func: Callable):
            cls._extractors.append(BaseExtractor.Extractor(name, func, requires))
            return func

        return decorator


class EchoesExtractor:
    def __init__(self, db: EchoesDB, paths: PathLibrary, force=False):
        self.db = db
        self.basic_loader = basics.BasicLoader(db)
        self.uni_loader = universe.UniverseLoader(self.basic_loader)
        self.path_library = paths
        self.force = force

    def extract_data(self, scopes: List[str]):
        order = BaseExtractor.find_order(scopes)
        msg = " - ".join(map(lambda extr: extr.name, order))
        logger.info("Extracting data in this order: %s", msg)
        for extractor in order:
            extractor.func(self)

    @classmethod
    def get_all_scopes(cls):
        return BaseExtractor.get_all_scopes()

    @BaseExtractor.extractor(name="lang")
    def load_lang(self, langs: Optional[List[str]] = None):
        if langs is None:
            langs = ["de", "en", "fr", "ja", "kr", "por", "ru", "spa", "zhcn"]
        self.basic_loader.load_language(base_path=self.path_library.path_gettext, lang="zh", copy_to="source")
        for lang in langs:
            self.basic_loader.load_language(base_path=self.path_library.path_gettext, lang=lang)

    @BaseExtractor.extractor(name="lang_cache", requires="lang")
    def load_localized_cache(self):
        self.basic_loader.load_localized_cache()

    @BaseExtractor.extractor(name="base", requires="lang_cache")
    def load_basics(self):
        self.basic_loader.load_dict_data(
            file=self.path_library.path_group, table=models.Group.__tablename__,
            schema={"zh_name": ("sourceName", str)}, localized={"localisedNameIndex": "zh_name"},
            default_values={"itemIds": "[]"},
            fields="id,itemIds,anchorable,anchored,fittableNonSingleton,iconPath,useBasePrice,localisedNameIndex,sourceName"
        )
        self.basic_loader.load_dict_data(
            file=self.path_library.path_category, table=models.Categories.__tablename__,
            schema={"zh_name": ("sourceName", str)}, localized={"localisedNameIndex": "zh_name"},
            # ToDo: Fix loading of groups (the ids are already in the file but not loaded)
            # default_values={"groupIds": "[]"},
            fields="id,groupIds,localisedNameIndex,sourceName"
        )
        if not self.path_library.path_item_type.exists():
            # File was not decompiled, import from pyc file
            self.uni_loader.load_item_types(
                path_script=self.path_library.path_script,
                path_item_types_by_group=self.path_library.path_item_types_by_group,
                path_type_id_mapping=self.path_library.path_type_id_mapping
            )
        else:
            # File was decompiled
            self.uni_loader.load_item_types(
                path_item_type=self.path_library.path_item_type,
                path_item_types_by_group=self.path_library.path_item_types_by_group,
                path_type_id_mapping=self.path_library.path_type_id_mapping
            )
        self.basic_loader.load_dict_data(
            file=self.path_library.path_units, table=models.Unit.__tablename__,
            fields="id,description,displayName,unitName"
        )

    @BaseExtractor.extractor(name="market_group", requires=["lang_cache"])
    def load_market_group(self):
        self.basic_loader.load_market_groups(
            path_market_group=self.path_library.path_market_sell
        )

    @BaseExtractor.extractor(name="attrs", requires=["lang_cache", "base"])
    def load_attributes(self):
        with open(self.path_library.path_tips_attr, "r", encoding="utf-8") as file:
            tips_map = json.load(file)["data"]
        attr_map = tips_map["equip_attr"]

        def get_attr_data(attr_key: str, attr_id: str, attr_ids: str):
            attr_ids = json.loads(attr_ids)
            data_key = next(filter(lambda i: str(i) in attr_map, [attr_id, *attr_ids]), None)
            if data_key is None:
                return None
            data_key = str(data_key)
            return attr_map[data_key][attr_key] if attr_key in attr_map[data_key] else None

        self.basic_loader.load_dict_data(
            file=self.path_library.path_attributes, table=models.Attribute.__tablename__,
            schema={"operator": ("attributeOperator", str), "to_attr_id": ("toAttrId", str)},
            calculated_fields=[
                ("attributeSourceUnit", ["id", "toAttrId"], functools.partial(get_attr_data, "attr_unit")),
                ("attributeSourceName", ["id", "toAttrId"], functools.partial(get_attr_data, "attr_name")),
                ("attributeTip", ["id", "toAttrId"], functools.partial(get_attr_data, "attr_tips")),
            ],
            localized={
                "unitLocalisationKey": "attributeSourceUnit",
                "nameLocalisationKey": "attributeSourceName",
                "tipLocalisationKey": "attributeTip",
            },
            zero_none_fields=["unitId"],
            fields="id,attributeCategory,attributeName,available,chargeRechargeTimeId,defaultValue,highIsGood,"
                   "maxAttributeId,attributeOperator,stackable,toAttrId,unitId,unitLocalisationKey,attributeSourceUnit,"
                   "attributeTip,attributeSourceName,nameLocalisationKey,tipLocalisationKey,attributeFormula"
        )

        self.basic_loader.load_dict_data(
            file=self.path_library.path_effects, table=models.Effect.__tablename__,
            zero_none_fields=["dischargeAttributeId", "durationAttributeId", "falloffAttributeId",
                              "fittingUsageChanceAttributeId", "rangeAttributeId", "trackingSpeedAttributeId"],
            fields="id,disallowAutoRepeat,dischargeAttributeId,durationAttributeId,effectCategory,effectName,"
                   "electronicChance,falloffAttributeId,fittingUsageChanceAttributeId,guid,isAssistance,isOffensive,"
                   "isWarpSafe,rangeAttributeId,rangeChance,trackingSpeedAttributeId"
        )

    @BaseExtractor.extractor(name="items", requires="lang_cache")
    def load_items(self):
        # ToDo: find preSkill, maybe exp? not sure about this one

        self.basic_loader.load_all_dict_data(
            root_path=self.path_library.path_items_root,
            table=models.Item,
            skip_existing=not self.force,
            primary_key="id",
            merge_with_file_path=self.path_library.path_items_dogma_root,
            schema={
                "zh_desc": ("sourceDesc", str),
                "zh_name": ("sourceName", str)
            },
            localized={
                "nameKey": "zh_name",
                "descKey": "zh_desc",
            },
            fields="id,canBeJettisoned,descSpecial,mainCalCode,sourceDesc,sourceName,marketGroupId,lockSkin,product,npcCalCodes,exp,published,corpCamera,abilityList,shipBonusCodeList,shipBonusSkillList,onlineCalCode,activeCalCode"
        )

        self.basic_loader.init_item_names()

        self.basic_loader.load_dict_data(
            file=self.path_library.path_item_nanocore, table=models.ItemNanocore.__tablename__,
            schema={
                "key": ("itemId", int),
                "main_affix": ("selectableModifierItems", str),
                "sub_affix": ("trainableModifierItems", str),
                "available_ship": ("availableShips", str)},
            localized={},
            # default_values={"trainableModifierItems": "[]", "availableShips": "[]"},
            fields="itemId,filmGroup,filmQuality,availableShips,selectableModifierItems,trainableModifierItems"
        )

    @BaseExtractor.extractor(name="item_extra", requires=["items", "base"])
    def load_item_extra(self):
        self.basic_loader.load_simple_data(
            file=self.path_library.path_repackage,
            root_key="data.group_ids",
            table=models.RepackageVolume.__tablename__,
            key_field="group_id",
            key_type=int,
            value_field="volume",
            value_type=float,
            do_logging=True
        )
        self.basic_loader.load_simple_data(
            file=self.path_library.path_repackage,
            root_key="data.type_ids",
            table=models.RepackageVolume.__tablename__,
            key_field="type_id",
            key_type=int,
            value_field="volume",
            value_type=float,
            do_logging=True
        )

        self.basic_loader.load_reprocess(
            file_path=self.path_library.path_reprocess
        )

    @BaseExtractor.extractor(name="bps", requires=["items", "attrs"])
    def load_blueprints(self):
        self.basic_loader.load_manufacturing(
            file_path=self.path_library.path_industry
        )

    @BaseExtractor.extractor(name="item_attrs", requires=["items", "attrs"])
    def load_item_attributes(self):
        self.basic_loader.load_all_item_attributes(
            root_path=self.path_library.path_dogma_root, regex=re.compile(r"type_attributes_\d+\.json"),
            table=models.ItemAttribute.__tablename__, columns=("itemId", "attributeId", "value")
        )

        self.basic_loader.load_item_attributes(
            file=self.path_library.path_type_effects, table=models.ItemEffects.__tablename__,
            columns=("itemId", "effectId", "isDefault")
        )

    @BaseExtractor.extractor(name="modifier")
    def load_item_modifier(self):
        # Todo: changeRangeModuleNames is missing
        self.basic_loader.load_dict_data(
            file=self.path_library.path_cal_codes_mod,
            dict_root_key="data.meta",
            table=models.ModifierDefinition.__tablename__,
            schema={
                "key": ("code", str),
                "change_types": ("changeTypes", str),
                "attribute_only": ("attributeOnly", bool),
                "change_ranges": ("changeRanges", str),
                "attribute_ids": ("attributeIds", str)
            },
            fields="code,changeTypes,attributeOnly,changeRanges,attributeIds,changeRangeModuleNames"
        )
        self.basic_loader.load_dict_data(
            file=self.path_library.path_cal_codes_mod,
            dict_root_key="data.code",
            table=models.ModifierValue.__tablename__,
            schema={
                "key": ("code", str),
                "attributes": ("attributes", str),
                "type_name": ("typeName", str),
            },
            fields="code,attributes,typeName"
        )
        self.basic_loader.init_item_modifiers()

    # ToDo: Find item_bonus_text
    # The descSpecial ids are already inside the items table, but the corresponding localisation ids are missing

    # ToDo: Add npc_equipment import from staticdata\py_data\data_common\static\dogma\npc_equipment.json

    # ToDo: Find market_group

    # ToDo: Find ship_modes
    # ToDo: Find ship_nanocore

    @BaseExtractor.extractor(name="universe", requires=["base", "lang_cache"])
    def load_universe(self):
        self.uni_loader.load_texts(file_path=self.path_library.path_universe_text)
        self.uni_loader.load_data(
            file_path="staticdata/sigmadata/eve/universe/regions.json",
            table="regions",
            columns=["id", "name", "x", "y", "z", "faction_id", "wormhole_class_id"])

        self.uni_loader.load_data(
            file_path=self.path_library.path_constellations,
            table="constellations",
            columns=["id", "name", "x", "y", "z", "faction_id", "radius", "wormhole_class_id"])

        solarsystems = self.uni_loader.load_data(
            file_path=self.path_library.path_solar_systems,
            table="solarsystems",
            columns=["id", "name", "x", "y", "z", "security", "faction_id", "radius", "region_id", "constellation_id"],
            return_raw=True, loading_bar=True)
        self.uni_loader.load_group_id_cache()
        self.uni_loader.load_system_cache()

        self.uni_loader.load_data(
            file_path=self.path_library.path_stars,
            table="celestials",
            columns=["id", "name",
                     # Compatible
                     ("type_id", lambda cel: self.uni_loader.type_to_short_id[cel["type_id"]]),
                     ("group_id", lambda cel: self.uni_loader.type_to_group_id[cel["type_id"]]),
                     ("system_id", "solar_system_id"), "x", "y", "z", "radius"],
            name_func=self.uni_loader.get_celestial_name,
            cache_celestials=True)

        self.uni_loader.load_data(
            file_path=self.path_library.path_celestials,
            table="celestials",
            columns=["id", "name",
                     ("type_id", lambda cel: self.uni_loader.type_to_short_id[cel["type_id"]]),
                     ("group_id", lambda cel: self.uni_loader.type_to_group_id[cel["type_id"]]),
                     ("system_id", "solar_system_id"), "orbit_id", "x", "y", "z", "radius",
                     "celestial_index", "orbit_index"],
            name_func=self.uni_loader.get_celestial_name,
            cache_celestials=True, loading_bar=True)

        stargates = self.uni_loader.load_data(
            file_path=self.path_library.path_stargates,
            table="celestials",
            columns=["id",
                     ("type_id", lambda cel: self.uni_loader.type_to_short_id[cel["type_id"]]),
                     ("group_id", lambda cel: self.uni_loader.type_to_group_id[cel["type_id"]]),
                     ("system_id", "from_solar_system_id"), "x", "y", "z"],
            cache_celestials=True, loading_bar=True, return_raw=True)
        self.uni_loader.load_stargates_connections(stargates)
        del stargates

    @BaseExtractor.extractor(name="cobalt", requires="universe")
    def load_map(self):
        logger.warning("Cobalt edge skipped")
        # ToDo: Remove warning, shouldn't be necessary when using latest staticdata export
        # self.uni_loader.init_cobalt_edge()

    @BaseExtractor.extractor(name="planet_exploit", requires=["universe", "items"])
    def load_pi(self):
        self.uni_loader.load_planetary_production(file_path=self.path_library.path_planet_exploit)

    @BaseExtractor.extractor(name="corp_tech", requires=["items"])
    def load_corp_tech(self):
        try:
            self.basic_loader.load_dict_data(
                file=self.path_library.path_corp_tech,
                dict_root_key="data.corp_task_item",
                table=models.CorpTaskItem.__tablename__,
                schema={
                    "key": ("itemId", int),
                    "fp_reward": ("fpReward", int),
                    "max_per_week": ("maxPerWeek", int),
                    "purchase_num": ("purchaseNum", int),
                    "random_group": ("randomGroup", int),
                    "week_times": ("weekTimes", int),
                },
                fields="itemId,fpReward,maxPerWeek,purchaseNum,randomGroup,weekTimes"
            )
        except KeyError as e:
            logger.error("Can't load corp tech items, data not found")
            logger.error(e)
        self.basic_loader.load_corp_tech(
            file=self.path_library.path_corp_tech,
        )
