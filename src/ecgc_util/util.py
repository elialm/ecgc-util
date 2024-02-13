from typing import Iterable, Iterator
import re
import logging

def scatter(collection: Iterable, chunk_size: int) -> Iterator[Iterable]:
    """Scatter an Iterable over multiple Iterables of a max length

    Args:
        collection (Iterable): Iterable to scatter
        chunk_size (int): maximum length of each chunk scattered.
        Must be larger than 1.

    Raises:
        ValueError: if chunk_size is an invalid value

    Yields:
        Iterator[Iterable]: slice after slice with a maximum length
        of chunk_size
    """

    if chunk_size < 1:
        raise ValueError('chunk_size must be 1 or higher')

    for i in range(0, len(collection), chunk_size):
        upper_bound = min(i + chunk_size, len(collection))
        yield collection[i:upper_bound]

__SIZE_MODIFIERS = {
    'k': 1024,
    'M': 1048576
}

def parse_size(size_string: str) -> int:
    """Parse a number with size specifier into an int

    Args:
        size_string (str): size with specifier

    Raises:
        ValueError: if size_string is not a number with size specifier

    Returns:
        int: integer corresponding to the size with specifier
    """
    res = re.match(r'^([0-9]+)(k|M)?$', size_string)
    if res:
        return int(res.group(1)) * __SIZE_MODIFIERS.get(res.group(2), 1)

    res = re.match(r'^0x([0-9A-Fa-f]+)$', size_string)
    if res:
        return int(res.group(1), 16)

    raise ValueError(
        'size \"{}\" is not in a supported format'.format(size_string))
    

__SIZE_COMPOSITION_DATA = (
    {
        'unit_size': 1048576,
        'unit_suffix': 'M'
    },
    {
        'unit_size': 1024,
        'unit_suffix': 'k'
    }
)

def compose_size(size: int) -> str:
    """Composes an integer size to its largest possible size specifier

    Args:
        size (int): size to compose

    Raises:
        ValueError: if size is a negative integer

    Returns:
        str: composed size
    """

    if size < 0:
        raise ValueError('size must be zero or a positive integer')

    for composition_data in __SIZE_COMPOSITION_DATA:
        if size % composition_data['unit_size'] == 0:
            return str(size // composition_data['unit_size']) + composition_data['unit_suffix']

    return str(size)

OUTPUT_LOG_LEVEL = 100

def logging_output(msg: object) -> None:
    logging.log(OUTPUT_LOG_LEVEL, msg)


__RGBDS_METAS = [
    {
        'pattern': re.compile(r'^-?\d+$'),
        'parser': lambda m: int(m.group(0))
    },
    {
        'pattern': re.compile(r'^\$([0-9A-Fa-f]+)$'),
        'parser': lambda m: int(m.group(1).lower(), 16)
    },
    {
        'pattern': re.compile(r'^%([01]+)$'),
        'parser': lambda m: int(m.group(1), 2)
    }
]

def parse_rgbds_int(number: str) -> int:
    """Parse an RGBDS assembler formatted integer into an integer

    Args:
        number (str): formatted integer

    Returns:
        int: parsed integer
    """

    for meta in __RGBDS_METAS:
        if res := re.match(meta['pattern'], number):
            return meta['parser'](res)
        
    raise ValueError('number is not in a valid integer format')
