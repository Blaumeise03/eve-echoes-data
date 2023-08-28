import logging
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
    db.load_data("staticdata/staticdata/dogma/attributes.json", "attributes",
                 schema={"operator": ("attributeOperator", str), "to_attr_id": ("toAttrId", str)},
                 fields="id,attributeCategory,attributeName,available,chargeRechargeTimeId,defaultValue,highIsGood,maxAttributeId,attributeOperator,stackable,toAttrId,unitId,unitLocalisationKey,attributeSourceUnit,attributeTip,attributeSourceName,nameLocalisationKey,tipLocalisationKey,attributeFormula")
    db.conn.close()
