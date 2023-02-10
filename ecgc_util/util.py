import re
import logging

__SIZE_MODIFIERS = {
    'k': 1024,
    'M': 1048576
}

def parse_size(size_string: str) -> int:
    res = re.match(r'^([0-9]+)(k|M)?$', size_string)
    if not res:
        raise ValueError(
            'size \"{}\" is not in a supported format'.format(size_string))

    return int(res.group(1)) * __SIZE_MODIFIERS.get(res.group(2), 1)

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
    if size < 0:
        raise ValueError('size must be zero or a positive integer')

    for composition_data in __SIZE_COMPOSITION_DATA:
        if size % composition_data['unit_size'] == 0:
            return str(size // composition_data['unit_size']) + composition_data['unit_suffix']

    return str(size)

OUTPUT_LOG_LEVEL = 100

def logging_output(msg: object) -> None:
    logging.log(OUTPUT_LOG_LEVEL, msg)
