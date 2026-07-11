import unittest
from buggy_code import greet

class TestGreeter(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("Atharva"), "Hello, Atharva")