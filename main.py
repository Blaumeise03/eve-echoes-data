import logging
import os
import re
import sqlite3
import sys
from collections import defaultdict

from echoes_data import database

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

ALLOWED_MODES = ["lang", "items", "item_attrs", "base", "modifier"]

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    db = database.EchoesDB()
    db.create_connection("echoes.db")
    db.setup_tables()
    print(sys.argv)
    modes = ALLOWED_MODES
    _arg_status = 0
    for arg in sys.argv:
        if arg.startswith("-"):
            _arg_status = 0
        if arg == "-m":
            _arg_status = 1
            modes = []
            continue
        if _arg_status == 1:
            if arg not in ALLOWED_MODES:
                raise Exception(f"Unknown import mode '{arg}'")
            modes.append(arg)

    if "base" in modes:
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
        db.load_dict_data(
            file="staticdata/staticdata/dogma/units.json", table="unit",
            fields="id,description,displayName,unitName"
        )
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
    if "base" in modes:
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
    if "item_attrs" in modes:
        db.load_all_item_attributes(
            root_path="staticdata/staticdata/dogma", regex=re.compile(r"type_attributes_\d+\.json"),
            table="item_attributes", columns=("itemId", "attributeId", "value")
        )
    if "base" in modes:
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
    # The descSpecial ids are aleady inside the items table, but the corresponding localisation ids are missing

    # modifier_definition staticdata\py_data\data_common\static\dogma\cal_code_modifier.json
    # modifier_value staticdata\py_data\data_common\static\dogma\cal_code_modifier.json
    # npc_equipment staticdata\py_data\data_common\static\dogma\npc_equipment.json
    #

    db.conn.close()
