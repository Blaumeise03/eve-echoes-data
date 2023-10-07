import argparse
import logging
import math
import sys
from typing import List, Optional

import sqlalchemy
# noinspection PyUnresolvedReferences
from colorama import just_fix_windows_console
from sqlalchemy import log as sqlalchemy_log

from echoes_data.data import Blueprint
from echoes_data.database import EchoesDB
from echoes_data.exceptions import DataNotFoundException
from echoes_data.utils import Dialect

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
        msg += f"\n    {'':<{max_l}}        {'='*14}===="
        msg += f"\n    {'':<{max_l}}        {isk:>14,.0f} ISK"
        print(msg)


def start_menu():
    print("====== Echoes Data CLI ======")
    print("Available Modes:")
    print("   bp - Get blueprint data")
    print("=============================")
    while True:
        mode = get_input("Please select a mode", ["bp", "exit"])
        match mode:
            case "quit":
                print("Good bye")
                engine.dispose()
                exit(0)
            case "bp":
                start_bp_menu()


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
