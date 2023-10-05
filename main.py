import argparse
import logging
import re
import sys

import sqlalchemy
# noinspection PyUnresolvedReferences
from colorama import just_fix_windows_console

from echoes_data.database import EchoesDB
from echoes_data import models
from echoes_data.utils import Dialect
from echoes_data.extractor import UniverseLoader, BasicLoader, EchoesExtractor, PathLibrary

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
ALL_MODES = EchoesExtractor.get_all_scopes()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Data extractor for the game Eve Echoes",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("root_path", type=str, help="The path to the staticdata folder")
    parser.add_argument("-m", "--mode",
                        type=str, nargs="+", choices=ALL_MODES,
                        default=ALL_MODES, help="The data that should be extracted")
    parser.add_argument("-db", "--database", type=str, default="sqlite+pysqlite:///echoes.db",
                        help="The url to the database, e.g. \nmariadb+mariadbconnector://user:password@localhost:3306/database")
    parser.add_argument("--dialect", type=str, choices=["sqlite", "mysql"], default="sqlite",
                        help="The database dialect, only sqlite and mysql are supported")

    args = parser.parse_args()
    just_fix_windows_console()

    # Sqlalchemy setup
    engine = sqlalchemy.create_engine(args.database,
                                      echo=False,
                                      pool_pre_ping=True,
                                      pool_recycle=True)

    db = EchoesDB(engine, dialect=Dialect.from_str(args.dialect))
    path_library = PathLibrary(args.root_path)
    missing = path_library.verify_files()
    if len(missing) > 0:
        logger.warning("There are %s files missing, depending on the selected mode the import might fail", len(missing))
        for k, p in missing:
            logger.warning("File %s not found: %s", k, p)
    else:
        logger.info("File paths using root_path %s verified", args.root_path)
    data_extractor = EchoesExtractor(db, path_library)
    data_extractor.extract_data(args.mode)
