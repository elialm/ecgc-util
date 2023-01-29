from .ecgc_spi_programmer import SpiProgrammer, ProgrammerException, SerialException

from argparse import ArgumentParser
from sys import stderr

def main_cli():
    parser = ArgumentParser(prog='ecgc-upload', description='Utility for uploading code to ecgc project cartridge')
    parser.add_argument('serial_port', help='Serial port of the spi programmer')

    args = parser.parse_args()

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