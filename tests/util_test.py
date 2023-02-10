import unittest

from ecgc_util.util import parse_size

class TestParseSize(unittest.TestCase):

    def test_without_appendix(self):
        self.assertEqual(parse_size('512'), 512)
        self.assertEqual(parse_size('1'), 1)

    def test_non_number(self):
        with self.assertRaises(ValueError):
            parse_size('hello')

    def test_with_kilo(self):
        self.assertEqual(parse_size('1k'), 1024)
        self.assertEqual(parse_size('4k'), 4096)

    def test_with_mega(self):
        self.assertEqual(parse_size('1M'), 1048576)
        self.assertEqual(parse_size('2M'), 2097152)

    def test_negative_number(self):
        with self.assertRaises(ValueError):
            parse_size('-1')
    
    def test_hexadecimal(self):
        self.assertEqual(parse_size('0x4000'), parse_size('16k'))
        self.assertEqual(parse_size('0x0'), 0)
