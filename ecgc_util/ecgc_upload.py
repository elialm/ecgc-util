from .spi_debug import SpiDebugger, DebuggerException, ProgrammerException, SerialException
from argparse import ArgumentParser
from sys import stderr
import re
import logging

__SIZE_MODIFIERS = {
    'k': 1024,
    'M': 1048576
}

__LOG_LEVELS = (
    logging.CRITICAL,
    logging.DEBUG
)


def parse_size(size_string: str) -> int:
    res = re.match(r'([0-9]+)(k|M)?', size_string)
    if not res:
        raise ValueError(
            'size \"{}\" is not in a supported format'.format(size_string))

    return int(res.group(1)) * __SIZE_MODIFIERS.get(res.group(2), 1)


def main_cli():
    parser = ArgumentParser(prog='ecgc-upload', description='Utility for uploading code to ecgc project cartridge')
    parser.add_argument('serial_port', help='Serial port of the spi programmer')
    parser.add_argument('image_file', help='File to upload to the cartridge')
    parser.add_argument('-s', '--size', default=0, help='Number for bytes to upload to the cartridge from the image file. If not given, will either upload entire file or fill the given target (if the file is equal of larger than the target)')
    parser.add_argument('-t', '--target', choices=('boot', 'dram', 'flash'), required=True, help='Destination target of the image upload')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity of program output')

    args = parser.parse_args()

    if args.size != 0:
        args.size = parse_size(args.size)

    logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s',
                        level=__LOG_LEVELS[min(args.verbose, len(__LOG_LEVELS) - 1)])

    try:
        with SpiDebugger(args.serial_port) as debugger:
            debugger.enable_auto_increment()
            debugger.set_address(0x4000)
    except (DebuggerException, ProgrammerException, SerialException) as e:
        logging.critical(e)


if __name__ == '__main__':
    main_cli()
