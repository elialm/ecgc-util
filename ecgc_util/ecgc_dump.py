from .spi_debugger import SpiDebugger, DebuggerException, SerialException
from .exception_debugging import log_info
from argparse import ArgumentParser
import logging

def main_cli():
    parser = ArgumentParser(prog='ecgc-dump', description='Utility for dumping memory from ecgc project cartridge')
    parser.add_argument('serial_port', help='Serial port of the spi programmer')
    parser.add_argument('output_file', help='File to output the dump')
    parser.add_argument('-n', type=str, required=True, help='Number of bytes to dump', dest='dump_size')
    parser.add_argument('-s', default='0', type=str, help='Number of bytes to dump', dest='start_offset')

    args = parser.parse_args()

    try:
        pass

    except (DebuggerException, SerialException) as e:
        logging.critical(e)
        log_info(e)
        exit(1)

if __name__ == '__main__':
    main_cli()
