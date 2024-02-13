import unittest

from src.ecgc_util.util import parse_size, scatter, parse_rgbds_int

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

class TestScatter(unittest.TestCase):

    def test_scatter_even_collection(self):
        collection = [99, 38, 3, 46, 59, 57, 68, 87, 42, 3, 27, 38, 38, 61, 49, 30]
        iterator = scatter(collection, 4)

        self.assertListEqual(next(iterator), [99, 38, 3, 46])
        self.assertListEqual(next(iterator), [59, 57, 68, 87])
        self.assertListEqual(next(iterator), [42, 3, 27, 38])
        self.assertListEqual(next(iterator), [38, 61, 49, 30])

        with self.assertRaises(StopIteration):
            next(iterator)

    def test_scatter_uneven_collection(self):
        collection = [99, 38, 3, 46, 59, 57, 68, 87, 42, 3, 27, 38, 38, 61, 49, 30]
        iterator = scatter(collection, 3)

        self.assertListEqual(next(iterator), [99, 38, 3])
        self.assertListEqual(next(iterator), [46, 59, 57])
        self.assertListEqual(next(iterator), [68, 87, 42])
        self.assertListEqual(next(iterator), [3, 27, 38])
        self.assertListEqual(next(iterator), [38, 61, 49])
        self.assertListEqual(next(iterator), [30])

        with self.assertRaises(StopIteration):
            next(iterator)

    def test_scatter_negative_size(self):
        collection = [99, 38, 3, 46, 59, 57, 68, 87, 42, 3, 27, 38, 38, 61, 49, 30]
        
        with self.assertRaises(ValueError):
            next(scatter(collection, -1))

    def test_scatter_zero_size(self):
        collection = [99, 38, 3, 46, 59, 57, 68, 87, 42, 3, 27, 38, 38, 61, 49, 30]
        
        with self.assertRaises(ValueError):
            next(scatter(collection, 0))

class TestParseRGBDSInt(unittest.TestCase):

    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_rgbds_int('hello world')

    def test_decimal(self):
        self.assertEqual(parse_rgbds_int('0'), 0)
        self.assertEqual(parse_rgbds_int('-1'), -1)
        self.assertEqual(parse_rgbds_int('69'), 69)

    def test_hexadecimal(self):
        self.assertEqual(parse_rgbds_int('$00'), 0)
        self.assertEqual(parse_rgbds_int('$69'), 0x69)
        self.assertEqual(parse_rgbds_int('$00001000'), 0x1000)

    def test_binary(self):
        self.assertEqual(parse_rgbds_int('%0'), 0)
        self.assertEqual(parse_rgbds_int('%1'), 1)
        self.assertEqual(parse_rgbds_int('%100'), 4)
        self.assertEqual(parse_rgbds_int('%10001000'), 0x88)
        