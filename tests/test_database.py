import unittest
from echoes_data import database


class DatabaseTest(unittest.TestCase):
    def test_correct_string(self):
        res = database.correct_string("{module_affix:联邦海军} {module:大型装甲连接模块}")
        self.assertEqual("{联邦海军} {大型装甲连接模块}", res)


if __name__ == '__main__':
    unittest.main()
