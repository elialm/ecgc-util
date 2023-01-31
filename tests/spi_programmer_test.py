import unittest

from ecgc_util.spi_programmer import scatter

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
