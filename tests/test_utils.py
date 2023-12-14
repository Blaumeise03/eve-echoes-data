import unittest

from echoes_data import data
from echoes_data.database import DataCache
from echoes_data.extractor import basics
from echoes_data.utils import *


class UtilsTest(unittest.TestCase):
    def test_correct_string(self):
        res = basics.correct_string("{module_affix:联邦海军} {module:大型装甲连接模块}")
        self.assertEqual("{联邦海军} {大型装甲连接模块}", res)

    def test_decapitalize(self):
        self.assertEqual("helloWORLD", decapitalize("HelloWORLD"))
        self.assertEqual("helloworld", decapitalize("helloworld"))
        self.assertEqual("hELLOWORLD", decapitalize("HELLOWORLD"))
        self.assertEqual("hELLOWORLD", decapitalize("helloworld", upper_rest=True))
        self.assertEqual("hELLOWORLD", decapitalize("HELLOWORLD", upper_rest=True))
        self.assertEqual("", decapitalize(""))
        self.assertEqual("", decapitalize("", upper_rest=True))
        self.assertEqual("h", decapitalize("H"))
        self.assertEqual("h", decapitalize("H", upper_rest=True))

    def test_snake_to_camel(self):
        self.assertEqual("hello", snake_to_camel("Hello"))
        self.assertEqual("helloWorld", snake_to_camel("Hello_world"))
        self.assertEqual("helloWorld", snake_to_camel("hello_world"))
        self.assertEqual("helloWorldHowAreYou", snake_to_camel("hello_world_how_are_you"))
        self.assertEqual("", snake_to_camel(""))

    def test_to_type(self):
        self.assertEqual(str, to_type("string"))
        self.assertEqual(int, to_type("int"))
        self.assertEqual(bool, to_type("bool"))
        self.assertEqual(float, to_type("float"))
        self.assertEqual(str, to_type("list"))
        self.assertEqual(None, to_type("42"))

    def test_load_schema(self):
        schema = {"attr_d_no_overwrite": ("attr_d_no_overwrite!!", int)}
        schema = load_schema("resources/example.schema.json", schema)
        self.assertCountEqual(
            ["key", "attr_a_int", "attr_b_bool", "attr_c_string", "attr_d_float", "attr_e_list", "attr_d_no_overwrite"],
            list(schema.keys())
        )
        self.assertEqual(("attrAInt", int), schema["attr_a_int"])
        self.assertEqual(("attrBBool", bool), schema["attr_b_bool"])
        self.assertEqual(("attrCString", str), schema["attr_c_string"])
        self.assertEqual(("attrDFloat", float), schema["attr_d_float"])
        self.assertEqual(("attrEList", str), schema["attr_e_list"])
        self.assertEqual(("attr_d_no_overwrite!!", int), schema["attr_d_no_overwrite"])
        self.assertEqual(("id", int), schema["key"])

    def test_caching(self):
        cache = DataCache()
        cache.add(data.Item(item_id=1234, name="Test 1234"))
        item = cache.get(data.Item, 1234)
        self.assertEqual("Test 1234", item.name)
        self.assertIs(item, cache.get_or_create(data.Item, 1234, item_id=1234, name="Test 1234"))
        self.assertEqual("Test 567", cache.get_or_create(data.Item, 567, item_id=567, name="Test 567").name)
        self.assertTrue(1234 in cache)
        self.assertTrue(item in cache)
        cache.free()
        self.assertFalse(1234 in cache)
        self.assertFalse(567 in cache)


if __name__ == '__main__':
    unittest.main()
