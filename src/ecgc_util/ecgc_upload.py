from .exception_debugging import log_info
from .uart_debugger import UartDebugger, DebuggerException, SerialException
from .util import parse_size, compose_size, logging_output
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
    parser.add_argument('serial_port', help='Serial port of the programmer')
    parser.add_argument('image_file', help='File to upload to the cartridge')
    parser.add_argument('-s', '--size', default='0', type=str, help='Number for bytes to upload to the cartridge from the image file. If not given, will either upload entire file or fill the given target (if the file is equal of larger than the target)')
    parser.add_argument('-t', '--target', choices=('boot', 'dram'), required=True, help='Destination target of the image upload')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity of program output')
    parser.add_argument('--version', action='version', version='%(prog)s 0.3a')

    args = parser.parse_args()

    # Configure logging
    logging.addLevelName(OUTPUT_LOG_LEVEL, 'OUTPUT')
    logging.basicConfig(format='%(levelname)8s - %(message)s',
                        level=__LOG_LEVELS[min(args.verbose, len(__LOG_LEVELS) - 1)])

    # Quit when targets are not implemented
    if args.target == 'dram':
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
    if args.size == 0:
        args.size = target_config['default_size']
        logging.warning('no size given, assuming default size of {} based on target'.format(compose_size(target_config['default_size'])))
        
    # Check for options based on target
    if args.size > target_config['max_size']:
        args.size = target_config['max_size']
        logging.warning('given size is larger than allowed, clipping it to {} based on target'.format(compose_size(target_config['max_size'])))

    # Time upload
    start_time = time.time()

    try:
        with UartDebugger(args.serial_port) as debugger:
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
        log_info(e)
        exit(1)

    time_elapsed = time.time() - start_time
    logging_output('upload finished successfully in {:.2f} seconds'.format(time_elapsed))


if __name__ == '__main__':
    main_cli()
