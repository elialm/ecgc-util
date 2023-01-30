import unittest

from ecgc_util.ecgc_upload import parse_size

class TestParseBytes(unittest.TestCase):

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
