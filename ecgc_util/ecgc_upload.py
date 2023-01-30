from .spi_programmer import SpiProgrammer, ProgrammerException, SerialException

from argparse import ArgumentParser
from sys import stderr
import re

__SIZE_MODIFIERS = {
    'k': 1024,
    'M': 1048576
}

def parse_size(size_string: str) -> int:
    res = re.match(r'([0-9]+)(k|M)?', size_string)
    if not res:
        raise ValueError('size \"{}\" is not in a supported format'.format(size_string))

    return int(res.group(1)) * __SIZE_MODIFIERS.get(res.group(2), 1)


def main_cli():
    parser = ArgumentParser(prog='ecgc-upload', description='Utility for uploading code to ecgc project cartridge')
    parser.add_argument('serial_port', help='Serial port of the spi programmer')
    parser.add_argument('image_file', help='File to upload to the cartridge')
    parser.add_argument('-s', '--size', default=0, help='Number for bytes to upload to the cartridge from the image file')
    parser.add_argument('-t', '--target', choices=('boot', 'dram', 'flash'), required=True, help='Destination target of the image upload')

    args = parser.parse_args()

    if args.size != 0:
        args.size = parse_size(args.size)

    try:
        programmer = SpiProgrammer(args.serial_port)
        programmer.enable()
        programmer.write(b'hello there general kenobi')
        programmer.disable()
    except ProgrammerException as e:
        print('ProgrammerException:', e, file=stderr)
    except SerialException as e:
        print('SerialException:', e, file=stderr)

if __name__ == '__main__':
    main_cli()