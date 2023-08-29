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

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    db = database.EchoesDB()
    db.create_connection("echoes.db")
    db.setup_tables()
    db.load_dict_data(
        file="staticdata/staticdata/dogma/attributes.json", table="attributes",
        schema={"operator": ("attributeOperator", str), "to_attr_id": ("toAttrId", str)},
        fields="id,attributeCategory,attributeName,available,chargeRechargeTimeId,defaultValue,highIsGood,maxAttributeId,attributeOperator,stackable,toAttrId,unitId,unitLocalisationKey,attributeSourceUnit,attributeTip,attributeSourceName,nameLocalisationKey,tipLocalisationKey,attributeFormula"
    )
    db.load_dict_data(
        file="staticdata/staticdata/dogma/effects.json", table="effects",
        fields="id,disallowAutoRepeat,dischargeAttributeId,durationAttributeId,effectCategory,effectName,electronicChance,falloffAttributeId,fittingUsageChanceAttributeId,guid,isAssistance,isOffensive,isWarpSafe,rangeAttributeId,rangeChance,trackingSpeedAttributeId"
    )
    db.load_dict_data(
        file="staticdata/staticdata/dogma/units.json", table="unit",
        fields="id,description,displayName,unitName"
    )
    for lang in ["de", "en", "fr", "ja", "kr", "por", "ru", "spa", "zhcn"]:
        db.load_language(base_path="staticdata/staticdata/gettext", lang=lang)
    db.load_language(base_path="staticdata/staticdata/gettext", lang="zh", copy_to="source")
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
    # ToDo: find preSkill, maybe exp? not sure about this one

    #conn = sqlite3.connect("echoes.db")
    #db.conn.backup(target=conn)
    #conn.close()
    db.conn.close()
