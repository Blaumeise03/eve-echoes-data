import argparse
import logging
import re
import sys

# noinspection PyUnresolvedReferences
from colorama import just_fix_windows_console

from echoes_data import database, universe, tables_setup
from echoes_data.universe import UniverseLoader

logger = logging.getLogger()
formatter = logging.Formatter(fmt="[%(asctime)s][%(levelname)s][%(name)s]: %(message)s")
# File log handler
# file_handler = logging.FileHandler(log_filename)
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)
# Console log handler
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logger.addHandler(console)
logger.setLevel("INFO")
ALL_MODES = ["lang", "items", "item_extra", "item_attrs", "bps", "base", "modifier", "universe", "planet_exploit"]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Patch notes scrapper for the game Eve Echoes")
    parser.add_argument("-m", "--mode",
                        type=str, nargs="+", choices=ALL_MODES,
                        default=ALL_MODES)
    parser.add_argument("--legacy", action=argparse.BooleanOptionalAction,
                        help="Uses the legacy db format from sweet")

    args = parser.parse_args()
    just_fix_windows_console()
    db = database.EchoesDB()
    db.create_connection("echoes.db")
    logger.info("Setting up tables")
    tables_setup.setup_basic_tables(db.conn, sweet_compatible=args.legacy)
    tables_setup.setup_universe_tables(db.conn)
    uni_loader = UniverseLoader(db)

    modes = args.mode

    if "lang" in modes:
        for lang in ["de", "en", "fr", "ja", "kr", "por", "ru", "spa", "zhcn"]:
            db.load_language(base_path="staticdata/staticdata/gettext", lang=lang)
        db.load_language(base_path="staticdata/staticdata/gettext", lang="zh", copy_to="source")
    else:
        logger.warning("Skipping language loading. It is recommended to load the language when the program is executed "
                       "the first time or the keys will be scrambled")
    db.load_localized_cache()
    if "base" in modes:
        db.load_dict_data(
            file="staticdata/staticdata/items/group.json", table="groups",
            schema={"zh_name": ("sourceName", str)}, localized={"localisedNameIndex": "zh_name"},
            default_values={"itemIds": "[]"},
            fields="id,itemIds,anchorable,anchored,fittableNonSingleton,iconPath,useBasePrice,localisedNameIndex,sourceName"
        )
        db.load_dict_data(
            file="staticdata/staticdata/items/category.json", table="categories",
            schema={"zh_name": ("sourceName", str)}, localized={"localisedNameIndex": "zh_name"},
            default_values={"groupIds": "[]"},
            fields="id,groupIds,localisedNameIndex,sourceName"
        )
        uni_loader.load_item_types(
            path_item_type="staticdata/script/data_common/static/item/item_type.py",
            path_item_types_by_group="staticdata/staticdata/items/item_types_by_group.json",
            path_type_id_mapping="staticdata/py_data/data_common/static/item/type_id_mapping.json")
        db.load_dict_data(
            file="staticdata/staticdata/dogma/units.json", table="unit",
            fields="id,description,displayName,unitName"
        )
    if "item_attrs" in modes:
        db.load_dict_data(
            file="staticdata/staticdata/dogma/attributes.json", table="attributes",
            schema={"operator": ("attributeOperator", str), "to_attr_id": ("toAttrId", str)},
            fields="id,attributeCategory,attributeName,available,chargeRechargeTimeId,defaultValue,highIsGood,"
                   "maxAttributeId,attributeOperator,stackable,toAttrId,unitId,unitLocalisationKey,attributeSourceUnit,"
                   "attributeTip,attributeSourceName,nameLocalisationKey,tipLocalisationKey,attributeFormula"
        )
        db.load_dict_data(
            file="staticdata/staticdata/dogma/effects.json", table="effects",
            fields="id,disallowAutoRepeat,dischargeAttributeId,durationAttributeId,effectCategory,effectName,"
                   "electronicChance,falloffAttributeId,fittingUsageChanceAttributeId,guid,isAssistance,isOffensive,"
                   "isWarpSafe,rangeAttributeId,rangeChance,trackingSpeedAttributeId"
        )
    if "items" in modes:
        # ToDo: find preSkill, maybe exp? not sure about this one
        db.load_all_dict_data(
            root_path="staticdata/staticdata/items", table="items",
            merge_with_file_path="staticdata/staticdata/items/item_dogma",
            schema={
                "zh_desc": ("sourceDesc", str),
                "zh_name": ("sourceName", str),
                "mining_exp_gain": ("exp", int)
            },
            localized={
                "nameKey": "zh_name",
                "descKey": "zh_desc",
            },
            default_values={
                "npcCalCodes": "[]",
                "normalDebris": "[]",
                "corpCamera": "[]",
                "abilityList": "[]",
                "shipBonusCodeList": "[]",
                "shipBonusSkillList": "[]",
                "descSpecial": "[]",
                "canBeJettisoned": False
            },
            fields="id,canBeJettisoned,descSpecial,mainCalCode,sourceDesc,sourceName,marketGroupId,lockSkin,product,npcCalCodes,exp,published,corpCamera,abilityList,shipBonusCodeList,shipBonusSkillList,onlineCalCode,activeCalCode"
        )
        db.load_dict_data(
            file="staticdata/staticdata/items/item_nanocore.json", table="item_nanocores",
            schema={
                "key": ("itemId", int),
                "main_affix": ("selectableModifierItems", str),
                "sub_affix": ("trainableModifierItems", str),
                "available_ship": ("availableShips", str)},
            localized={},
            default_values={"trainableModifierItems": "[]", "availableShips": "[]"},
            fields="itemId,filmGroup,filmQuality,availableShips,selectableModifierItems,trainableModifierItems"
        )
        db.load_simple_data(
            file="staticdata/py_data/data_common/static/item/repackage_volume.json",
            root_key="data.group_ids",
            table="repackage_volume",
            key_field="group_id",
            key_type=int,
            value_field="volume",
            value_type=float,
            logging=True
        )
    if "item_extra" in modes:
        db.load_simple_data(
            file="staticdata/py_data/data_common/static/item/repackage_volume.json",
            root_key="data.type_ids",
            table="repackage_volume",
            key_field="type_id",
            key_type=int,
            value_field="volume",
            value_type=float,
            logging=True
        )
        db.load_reprocess(
            file_path="staticdata/py_data/data_common/static/reprocess.json"
        )
    if "bps" in modes:
        db.load_manufacturing(
            file_path="staticdata/py_data/data_common/static/spacestation/industry.json"
        )
    if "item_attrs" in modes:
        db.load_all_item_attributes(
            root_path="staticdata/staticdata/dogma", regex=re.compile(r"type_attributes_\d+\.json"),
            table="item_attributes", columns=("itemId", "attributeId", "value")
        )
        db.load_item_attributes(
            file="staticdata/staticdata/dogma/type_effects.json", table="item_effects",
            columns=("itemId", "effectId", "isDefault")
        )
    if "modifier" in modes:
        # Todo: changeRangeModuleNames is missing
        db.load_dict_data(
            file="staticdata/py_data/data_common/static/dogma/cal_code_modifier.json",
            dict_root_key="data.meta",
            table="modifier_definition",
            schema={
                "key": ("code", str),
                "change_types": ("changeTypes", str),
                "attribute_only": ("attributeOnly", bool),
                "change_ranges": ("changeRanges", str),
                "attribute_ids": ("attributeIds", str)
            },
            default_values={
                "changeTypes": "[]",
                "changeRanges": "[]",
                "attributeIds": "[]",
                "attributeOnly": False,
                "changeRangeModuleNames": "[]"
            },
            fields="code,changeTypes,attributeOnly,changeRanges,attributeIds,changeRangeModuleNames"
        )
        db.load_dict_data(
            file="staticdata/py_data/data_common/static/dogma/cal_code_modifier.json",
            dict_root_key="data.code",
            table="modifier_value",
            schema={
                "key": ("code", str),
                "attributes": ("attributes", str),
                "type_name": ("typeName", str),
            },
            fields="code,attributes,typeName"
        )
        db.init_item_modifiers()

    # ToDo: Find item_bonus_text
    # The descSpecial ids are already inside the items table, but the corresponding localisation ids are missing

    # ToDo: Add npc_equipment import from staticdata\py_data\data_common\static\dogma\npc_equipment.json

    # ToDo: Find market_group

    # ToDo: Find ship_modes
    # ToDo: Find ship_nanocore

    if "universe" in modes:
        uni_loader.load_texts("staticdata/sigmadata/eve/universe/gettext.json")
        uni_loader.load_data(
            file_path="staticdata/sigmadata/eve/universe/regions.json",
            table="regions",
            columns=["id", "name", "x", "y", "z", "faction_id", "wormhole_class_id"])
        uni_loader.load_data(
            file_path="staticdata/sigmadata/eve/universe/constellations.json",
            table="constellations",
            columns=["id", "name", "x", "y", "z", "faction_id", "radius", "wormhole_class_id"])
        uni_loader.load_data(
            file_path="staticdata/sigmadata/eve/universe/solar_systems.json",
            table="solarsystems",
            columns=["id", "name", "x", "y", "z", "security", "faction_id", "radius", "region_id", "constellation_id"],
            extra_task=universe.add_solarsystem_neighbours)
        uni_loader.load_group_id_cache()
        uni_loader.load_system_cache()
        uni_loader.load_data(
            file_path="staticdata/sigmadata/eve/universe/stars.json",
            table="celestials",
            columns=["id", "name",
                     # Compatible
                     ("type_id", lambda cel: uni_loader.type_to_short_id[cel["type_id"]]),
                     ("group_id", lambda cel: uni_loader.type_to_group_id[cel["type_id"]]),
                     ("system_id", "solar_system_id"), "orbit_id", "x", "y", "z", "radius",
                     "celestial_index", "orbit_index"],
            name_func=uni_loader.get_celestial_name,
            cache_celestials=True)
        uni_loader.load_data(
            file_path="staticdata/sigmadata/eve/universe/celestials.json",
            table="celestials",
            columns=["id", "name",
                     ("type_id", lambda cel: uni_loader.type_to_short_id[cel["type_id"]]),
                     ("group_id", lambda cel: uni_loader.type_to_group_id[cel["type_id"]]),
                     ("system_id", "solar_system_id"), "orbit_id", "x", "y", "z", "radius",
                     "celestial_index", "orbit_index"],
            name_func=uni_loader.get_celestial_name,
            cache_celestials=True, loading_bar=True)
    if "planet_exploit" in modes:
        uni_loader.load_planetary_production("staticdata/manual_staticdata/universe/planet_exploit_resource.json")

    db.conn.close()
