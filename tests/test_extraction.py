import unittest
from pathlib import Path

import sqlalchemy
from sqlalchemy import text

from echoes_data import models
from echoes_data.database import EchoesDB
from echoes_data.extractor import EchoesExtractor, PathLibrary
from echoes_data.utils import Dialect


class ExtractionTest(unittest.TestCase):
    engine = None  # type: sqlalchemy.Engine | None
    db = None  # type: EchoesDB | None
    paths = None  # type: PathLibrary | None
    data_extractor = None  # type: EchoesExtractor | None

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = sqlalchemy.create_engine("sqlite+pysqlite:///echoes_test.db",
                                              echo=False,
                                              pool_pre_ping=True,
                                              pool_recycle=True)

        # Enforce foreign keys in sqlite
        def _fk_pragma_on_connect(dbapi_con, con_record):
            dbapi_con.execute('pragma foreign_keys=ON')

        from sqlalchemy import event
        event.listen(cls.engine, 'connect', _fk_pragma_on_connect)

        models.Base.metadata.drop_all(bind=cls.engine, checkfirst=True)
        cls.db = EchoesDB(cls.engine, dialect=Dialect.sqlite)
        cls.paths = PathLibrary(Path("resources/example_staticdata"))
        cls.data_extractor = EchoesExtractor(cls.db, cls.paths)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_0_paths(self):
        return
        missing = self.paths.verify_files()
        self.assertEqual(0, len(missing), "There are missing example static data files")

    def test_1_extract_lang(self):
        self.data_extractor.load_lang(["en"])
        with self.engine.connect() as conn:
            stmt = text("SELECT id, en, source FROM localised_strings WHERE id=1")
            res = conn.execute(stmt).fetchone()
        self.assertEqual((1, "Test string A en", "Test string A zh"), res)

    def test_2_load_lang_cache(self):
        self.data_extractor.basic_loader.strings.clear()
        self.data_extractor.basic_loader.strings_en.clear()
        self.data_extractor.load_localized_cache()
        self.assertEqual(10, len(self.data_extractor.basic_loader.strings), "Strings cache is invalid")
        self.assertEqual(10, len(self.data_extractor.basic_loader.strings_en), "Strings_en cache is invalid")

    def test_3_load_basics(self):
        self.data_extractor.load_basics()
        with self.engine.connect() as conn:
            stmt = text("SELECT id, name, anchorable, anchored, fittableNonSingleton, iconPath, useBasePrice, "
                        "localisedNameIndex, sourceName, itemIds "
                        "FROM groups")
            expected = [
                (10000, "GroupA", 0, 0, 0, "group_1_icon.png", 0, 2, "Group 1 zh", "[]"),
                (10001, "GroupB", 1, 1, 1, "", 1, 3, "Group 2 zh", "[]"),
                (10002, "GroupC", 0, 0, 0, "", 0, 4, "Group 3 zh", "[]")
            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Group loading failed")
            stmt = text("SELECT id, name, groupIds, localisedNameIndex, sourceName FROM categories")
            expected = [
                (10, "CategoryA", "[]", 5, "Category 0 zh"),
                (11, "CategoryB", "[]", 6, "Category 1 zh")
            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Category loading failed")
            stmt = text("SELECT id, short_id, name, group_id FROM types")
            expected = [
                (20000, 1, "TypeA", 10000),
                (20001, 2, "TypeB", 10000),
                (20002, 3, "TypeC", 10001)
            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Type loading failed")
            stmt = text("SELECT id, description, displayName, unitName FROM unit")
            expected = [
                (1, "UnitA", "a", "Length"),
                (2, "UnitB", "b", "Length")
            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Unit loading failed")

    def test_4_load_attributes(self):
        self.data_extractor.load_attributes()
        with self.engine.connect() as conn:
            stmt = text("SELECT "
                        "   id, attributeCategory, attributeName, available, chargeRechargeTimeId, defaultValue, highIsGood "
                        "FROM attributes")
            expected = [
                (1, 10, "attrA", 1, 0, 0.5, 1),
                (2, 11, "attrB", 0, 1, 1, 0)
            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Attributes loading failed")
            stmt = text("SELECT "
                        "   id, effectName, effectCategory, disallowAutoRepeat, guid, isAssistance, isOffensive "
                        "FROM effects")
            expected = [
                (1, "effectA", 1, 0, "effects.A", 0, 1)
            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Effect loading failed")

    def test_5_load_items(self):
        self.data_extractor.load_items()
        with self.engine.connect() as conn:
            stmt = text("SELECT "
                        "   id, mainCalCode, sourceName, sourceDesc, nameKey, descKey, marketGroupId "
                        "FROM items")
            expected = [
                (30001, "/Cal/Code/1/", "Item A (zh)", "Item A description (zh)", 10, 9, 2000001),
                (30002, "", "Nanocore (zh)", "Nanocore description (zh)", 7, 8, None)
            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Item loading failed")

    def test_6_load_item_extra(self):
        self.data_extractor.load_item_extra()
        with self.engine.connect() as conn:
            stmt = text("SELECT group_id, type_id, volume FROM repackage_volume")
            expected = [
                (10000, None, 500),
                (10001, None, 600),
                (None, 30001, 10),
                (None, 30002, 20),

            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Repackage volume loading failed")
            stmt = text("SELECT itemId, resultId, quantity FROM reprocess")
            expected = [
                (30001, 30002, 143)
            ]
            res = conn.execute(stmt).fetchall()
            self.assertCountEqual(expected, res, "Repackage volume loading failed")


if __name__ == '__main__':
    unittest.main()
