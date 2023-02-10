from .spi_debugger import SpiDebugger, DebuggerException, SerialException
from .exception_debugging import log_info
from .util import parse_size, logging_output, compose_size
from argparse import ArgumentParser
import logging
import time


READ_BUFFER_SIZE = 1024

OUTPUT_LOG_LEVEL = 100
__LOG_LEVELS = (
    logging.WARNING,
    logging.INFO,
    logging.DEBUG
)

def main_cli():
    parser = ArgumentParser(prog='ecgc-dump', description='Utility for dumping memory from ecgc project cartridge')
    parser.add_argument('serial_port', help='Serial port of the spi programmer')
    parser.add_argument('output_file', help='File to output the dump')
    parser.add_argument('-n', type=str, required=True, help='Number of bytes to dump', dest='dump_size')
    parser.add_argument('-s', default='0', type=str, help='Number of bytes to skip from the start', dest='start_offset')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity of program output')

    args = parser.parse_args()

    # Configure logging
    logging.addLevelName(OUTPUT_LOG_LEVEL, 'OUTPUT')
    logging.basicConfig(format='%(levelname)8s - %(message)s',
                        level=__LOG_LEVELS[min(args.verbose, len(__LOG_LEVELS) - 1)])

    # Parse dump_size value
    try:
        args.dump_size = parse_size(args.dump_size)
    except ValueError as e:
        logging.critical('error while parsing DUMP_SIZE: {}'.format(str(e)))
        exit(1)

    # Parse start_offset value
    try:
        args.start_offset = parse_size(args.start_offset)
    except ValueError as e:
        logging.critical('error while parsing START_OFFSET: {}'.format(str(e)))
        exit(1)

    # Check whether start offset and dump size do not exceed the memory map
    if (args.start_offset + args.dump_size) > 0x10000:
        logging.warning('dump exceeds cartridge memory map, clipping address to not exceed address 0xFFFF')
        args.dump_size -= (args.start_offset + args.dump_size) - 0x10000

    # Time dump
    start_time = time.time()

    try:
        with SpiDebugger(args.serial_port) as debugger:
            debugger.enable_auto_increment()
            debugger.set_address(args.start_offset)

            bytes_left = args.dump_size
            with open(args.output_file, 'wb') as output_file:
                while bytes_left > 0:
                    read_amount = min(bytes_left, READ_BUFFER_SIZE)
                    chunk = debugger.read(read_amount)
                    output_file.write(chunk)
                    bytes_left -= len(chunk)

    except (DebuggerException, SerialException) as e:
        logging.critical(e)
        log_info(e)
        exit(1)

    time_elapsed = time.time() - start_time
    logging_output('dumped {}B successfully in {:.2f} seconds'.format(compose_size(args.dump_size), time_elapsed))

if __name__ == '__main__':
    main_cli()
