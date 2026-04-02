import unittest

from webapp.main import jsonable


class TestJsonable(unittest.TestCase):
    def test_jsonable_converts_tuples(self):
        x = {"a": (1, 2, (3, 4)), "b": [{"c": (5, 6)}]}
        y = jsonable(x)
        self.assertEqual(y["a"], [1, 2, [3, 4]])
        self.assertEqual(y["b"][0]["c"], [5, 6])


if __name__ == "__main__":
    unittest.main()

