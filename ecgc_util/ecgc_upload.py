from .spi_debugger import SpiDebugger, DebuggerException, SerialException
from argparse import ArgumentParser
from sys import stderr
import re
import logging


__SIZE_MODIFIERS = {
    'k': 1024,
    'M': 1048576
}

def parse_size(size_string: str) -> int:
    res = re.match(r'([0-9]+)(k|M)?', size_string)
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

READ_BUFFER_SIZE = 1024

__LOG_LEVELS = (
    logging.WARNING,
    logging.DEBUG
)

__TARGET_CONFIGS = {
    'boot': {
        'max_size': parse_size('4k'),
        'default_size': parse_size('4k'),
        'start_address': 0x0000
    },
    'dram': None,
    'flash': None
}

def main_cli():
    parser = ArgumentParser(prog='ecgc-upload', description='Utility for uploading code to ecgc project cartridge')
    parser.add_argument('serial_port', help='Serial port of the spi programmer')
    parser.add_argument('image_file', help='File to upload to the cartridge')
    parser.add_argument('-s', '--size', default=0, help='Number for bytes to upload to the cartridge from the image file. If not given, will either upload entire file or fill the given target (if the file is equal of larger than the target)')
    parser.add_argument('-t', '--target', choices=('boot', 'dram', 'flash'), required=True, help='Destination target of the image upload')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity of program output')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s',
                        level=__LOG_LEVELS[min(args.verbose, len(__LOG_LEVELS) - 1)])

    # Quit when targets are not implemented
    if args.target == 'dram' or args.target == 'flash':
        logging.critical('target {} is not yet implemented'.format(args.target))
        exit(1)

    target_config = __TARGET_CONFIGS[args.target]

    # Parse size value
    try:
        args.size = parse_size(args.size)
    except ValueError as e:
        logging.critical(e)
        exit(1)

    # Configure size of upload
    if args.size < 0:
        logging.critical('negative sizes are not allowed')
        exit(1)
    elif args.size == 0:
        args.size = target_config['default_size']
        logging.warning('no size given, assuming default size of {} based on target'.format(compose_size(target_config['default_size'])))
        

    # Check for options based on target
    if args.size > target_config['max_size']:
        args.size = target_config['max_size']
        logging.warning('given size is larger than allowed, clipping it to {} based on target'.format(compose_size(target_config['max_size'])))

    try:
        with SpiDebugger(args.serial_port) as debugger:
            debugger.enable_auto_increment()
            debugger.set_address(target_config['start_address'])

            bytes_left = args.size
            with open(args.image_file, mode='rb') as image_file:
                while bytes_left > 0:
                    read_amount = min(bytes_left, READ_BUFFER_SIZE)
                    chunk = image_file.read(read_amount)
                    debugger.write(chunk)
                    bytes_left -= len(chunk)
                    
            if bytes_left != 0:
                logging.warning('given size argument expects more bytes to be written ({} left)'.format(bytes_left))

    except (DebuggerException, SerialException) as e:
        logging.critical(e)
        exit(1)


if __name__ == '__main__':
    main_cli()
