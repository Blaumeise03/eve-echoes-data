import argparse
import logging
import sys
from pathlib import Path

import sqlalchemy
# noinspection PyUnresolvedReferences
from colorama import just_fix_windows_console

from echoes_data import utils
from echoes_data.database import EchoesDB
from echoes_data.extractor import EchoesExtractor, PathLibrary
from echoes_data.utils import Dialect

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
    parser.add_argument("--only_list_files", action="store_true",
                        help="Instead of extracting the data, a list of all required files will get printed")
    parser.add_argument("-d", "--drop", action="store_true",
                        help="Drops all tables before reloading the data (doesn't affect third-party tables)")
    parser.add_argument("-f", "--force_replace", action="store_true",
                        help="Forces the refresh of the data and does not skip any already existing data")

    args = parser.parse_args()

    utils.enable_global_loading_bar()

    logger = logging.getLogger()
    formatter = logging.Formatter(fmt="[%(asctime)s][%(levelname)s][%(name)s]: %(message)s")
    logger.setLevel("INFO")

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger.addHandler(console)

    path_library = PathLibrary(args.root_path)
    missing = path_library.verify_files()
    if args.only_list_files:
        logger.info("====== Required files ======")
        for name, path in path_library.get_file_list():
            name = name.replace("path_", "")
            logger.info(f"{name: <19}: %s", path)
        exit(0)

    if len(missing) > 0:
        logger.warning("There are %s files missing, depending on the selected mode the import might fail", len(missing))
        for k, p in missing:
            logger.warning("File %s not found: %s", k, p)
    else:
        logger.info("File paths using root_path %s verified", args.root_path)

    # Sqlalchemy setup
    engine = sqlalchemy.create_engine(args.database,
                                      echo=False,
                                      pool_pre_ping=True,
                                      pool_recycle=True)

    db = EchoesDB(engine, dialect=Dialect.from_str(args.dialect))
    data_extractor = EchoesExtractor(db, path_library, force=args.force_replace)
    data_extractor.uni_loader.python27_exe = Path("legacy_adapter/venv/Scripts/python.exe")
    if args.drop:
        data_extractor.basic_loader.drop_tables()
    data_extractor.basic_loader.init_db()
    data_extractor.extract_data(args.mode)
