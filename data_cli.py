import argparse
import logging
import math
import sys
from typing import List, Optional

import sqlalchemy
# noinspection PyUnresolvedReferences
from colorama import just_fix_windows_console
from sqlalchemy import log as sqlalchemy_log, select, text

from echoes_data import models, utils
from echoes_data.data import Blueprint
from echoes_data.database import EchoesDB
from echoes_data.exceptions import DataNotFoundException
from echoes_data.utils import Dialect
from echoes_data.utils._console import LoadingConsole

sqlalchemy_log._add_default_handler = lambda x: None  # Patch to avoid duplicate logging

logger = logging.getLogger()
formatter = logging.Formatter(fmt="[%(asctime)s][%(levelname)s][%(name)s]: %(message)s")
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logger.addHandler(console)
logger.setLevel("INFO")


def get_input(msg: str, choices: Optional[List[str]] = None):
    res = input(msg)
    if choices is None:
        return res.strip()
    if res not in choices:
        print(f"Invalid input '{res}', it must be one of the following:")
        print(", ".join(choices))
        return get_input(msg, choices)
    return res


def start_bp_menu():
    while True:
        item_name = get_input("Please enter an item name (or exit to leave)")
        if item_name == "exit":
            return
        try:
            blueprint = db.fetch_blueprint(item_name, recursive=True)
        except DataNotFoundException as e:
            print(f"Item/Blueprint not found: {e}")
            continue
        effi = get_input("Please enter an efficiency (e.g. 95 for 95%)").rstrip("%")
        try:
            effi = int(effi) / 100
        except TypeError:
            print("Input must be a number")
            continue
        msg = (f"Item: {blueprint.product.name}\n"
               f"Blueprint: {blueprint.name}\n"
               f"Money: {blueprint.money:,.0f} ISK\n"
               f"Time: {blueprint.time}\n"
               f"Decryptor Mult: {blueprint.decryptor_mult}\n"
               f"Resources (with {effi:.0%}%):")
        full_cost = blueprint.calculate_costs(effi)
        res_type_len = {}
        for cost in blueprint.resources:
            if cost.type in res_type_len:
                if len(cost.item.name) > res_type_len[cost.type]:
                    res_type_len[cost.type] = len(cost.item.name)
            else:
                res_type_len[cost.type] = len(cost.item.name)
        last_type = None
        for cost in blueprint.resources:
            if cost.type != last_type:
                msg += f"\n  ===== {cost.type.name} ====="
                last_type = cost.type
            msg += f"\n    {cost.item.name:<{res_type_len[cost.type]}}: {math.ceil(cost.amount * effi)}"
        full_order = sorted(full_cost.keys(), key=lambda i: i.id)
        max_l = max(res_type_len.values())
        msg += "\n======= Total Costs ======="
        isk = 0
        for item in full_order:
            msg += f"\n    {item.name:<{max_l}}: {full_cost[item]:>2,.0f}"
            if isinstance(item, Blueprint):
                price = item.money * full_cost[item]
                isk += price
                msg += f"  + {price:>14,.0f} ISK"
        isk += blueprint.money
        msg += f"\n    {blueprint.name:<{max_l}}:  1  + {blueprint.money:>14,.0f} ISK"
        msg += f"\n    {'':<{max_l}}        {'=' * 14}===="
        msg += f"\n    {'':<{max_l}}        {isk:>14,.0f} ISK"
        print(msg)


def start_csv_menu():
    print("Please enter what you want to export: blueprints")
    sel = get_input("What do you want to export?", ["blueprints"])
    if sel == "blueprints":
        print("Please prepare a file containing all resources that should get exported. The resources should be "
              "separated by a tabulator or a line break.")
        raw = input("Header file: ")
        resources = []
        with open(raw, "r", encoding="utf-8") as file:
            lines = file.readlines()
        for line in lines:
            resources.extend(map(lambda s: s.strip(), line.strip(" \n").split("\t")))
        print(f"Found {len(resources)} resources in header file")
        resource_ids = []
        stmt = select(models.Item.name, models.Item.id).where(models.Item.name.in_(resources))
        with engine.connect() as conn:
            res = conn.execute(stmt).fetchall()
            for wanted in resources:
                found = False
                for r_n, r_i in res:
                    if r_n == wanted:
                        resource_ids.append(r_i)
                        found = True
                        break
                if found:
                    continue
                print("Resource not found: " + wanted)
                return

        sql = "SELECT item.name"

        def _get_subquery(r_name: str, r_id: int):
            return (",\n       (SELECT bc.amount\n"
                    "        FROM blueprint_costs as bc\n"
                    "                 JOIN items i on bc.resourceId = i.id\n"
                    f"        WHERE i.id={r_id}\n"
                    f"          AND bc.blueprintId = bp.blueprintId) AS '{r_name}'")
        for res_name, res_id in zip(resources, resource_ids):
            sql += _get_subquery(res_name, res_id)
        sql += ("\nFROM blueprints as bp\n"
                "         JOIN items item on bp.productId = item.id"
                )
        print("Loading data")
        with engine.connect() as conn:
            res = conn.execute(text(sql)).fetchall()
        print(f"Loaded {len(res)} rows, writing to csv file...")
        with open("staticdata/blueprints.csv", "w", encoding="utf-8") as csv:
            csv.write("Product,")
            csv.write(",".join(resources))
            csv.write("\n")
            for row in res:
                csv.write(",".join([str(col) if col is not None else "0" for col in row]))
                csv.write("\n")
        print("File exported, saved as staticdata/blueprints.csv")
        return


def start_menu():
    print("====== Echoes Data CLI ======")
    print("Available Modes:")
    print("   bp  - Get blueprint data")
    print("   csv - CSV export tools")
    print("=============================")
    while True:
        mode = get_input("Please select a mode", ["bp", "csv", "exit"])
        match mode:
            case "quit":
                print("Good bye")
                engine.dispose()
                exit(0)
            case "bp":
                start_bp_menu()
            case "csv":
                start_csv_menu()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Data extractor for the game Eve Echoes",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-db", "--database", type=str, default="sqlite+pysqlite:///echoes.db",
                        help="The url to the database, e.g. \nmariadb+mariadbconnector://user:password@localhost:3306/database")
    parser.add_argument("--dialect", type=str, choices=["sqlite", "mysql"], default="sqlite",
                        help="The database dialect, only sqlite and mysql are supported")

    args = parser.parse_args()

    # Sqlalchemy setup
    engine = sqlalchemy.create_engine(args.database,
                                      echo=False,
                                      pool_pre_ping=True,
                                      pool_recycle=True)

    db = EchoesDB(engine, dialect=Dialect.from_str(args.dialect))
    start_menu()
