from .exception_debugging import log_info
from .uart_debugger import UartDebugger, DebuggerException, SerialException
from argparse import ArgumentParser, RawTextHelpFormatter, ArgumentError, Namespace
import logging
import re
import sys
import cmd


OUTPUT_LOG_LEVEL = 100
__LOG_LEVELS = (
    logging.WARNING,
    logging.INFO,
    logging.DEBUG
)

__EPILOG = """
The utility will open a command prompt for entering commands. Usable commands
are documented below. These commands give the user the ability to peek and poke
at registers inside the cartridge's memory space.

Do note that the DMA registers are NOT accessible through the debug core due to
the firmware architecture.

Also note that all address operations must occur with the address range of
0x0000-0xFFFF. Any operations outside this range will raise an error and be
cancelled.

## Available commands

    - read address [-f/--fixed] [-s/--size SIZE]
    - write address [-f/--fixed] [-s/--signed] [-r/--repeat TIMES] data

## Integer formatting

All integers passed can be formatted as decimal, hexadecimal or binary. The
formatting rules follow the RGBDS assembly format. This means that the
formatting rules are as follows:

    - Decimal (default): <number> (e.g. 1 or 69)
    - Hexadecimal: $<number> (e.g. $EF or $4000)
    - Binary: %<number> (e.g. %00110010 or %10)

Leading zeros are not necessary when there's a need of a specific integer size.
For example, the 16-bit address $0100 may also be written as $100.

## Read command

The read command reads from the specified address. An optional size parameter
can be passed to specify how many bytes are to be read. By default, the size
will be 1.

When reading multiple bytes, the address will be incremented at each received
byte. To disable this behaviour and fix the address at the given value, add
the -f/--fixed flag.

### Read examples

- Read a single byte from address $4000
    > read $4000
- Read 16 bytes from addresses $0100-$01FF
    > read $0100 16
- Read 256 bytes from address $A100
    > read $A100 -f 256

## Write command

The write command writes the given data to the specified address. When writing
multiple bytes, the address will be incremented at each received byte. To
disable this behaviour and fix the address at the given value, add the
-f/--fixed flag.

The data is given as a series of bytes separated by a space. Each value must
fit within an 8-bit unsigned integer. To write unsigned data, add the
-s/--signed flag.

Data can also be given as a repeated pattern. When specifying the -r/--repeat
flag, one can give a number TIMES which repeats the given data pattern TIMES
times.

### Write examples

- Write a single byte to address $4000
    > write $4000 $FF
- Write the numbers 1-16 to addresses $0100-$01FF
    > write $0100 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
- Write 256 bytes to address $A100
    > write $A100 -f 256
- Write $00 to addresses $4000-$7FFF
    > write $4000 -r $4000 $00
"""

class CommandError(Exception):
    pass

class SubArgumentParser(ArgumentParser):
    def error(self, message):
        raise ArgumentError(None, message)

def construct_parser_read() -> SubArgumentParser:
    parser = SubArgumentParser(prog='read', add_help=False, exit_on_error=False)
    parser.add_argument('address', help='address to read from')
    parser.add_argument('-f', '--fixed', action='store_true', help='disable address increment on multi-byte operations')
    parser.add_argument('-s', '--size', default='1', help='number of bytes to read. defaults to 1')

    return parser

def construct_parser_write() -> SubArgumentParser:
    parser = SubArgumentParser(prog='write', add_help=False, exit_on_error=False)
    parser.add_argument('address')
    parser.add_argument('-f', '--fixed', action='store_true')
    parser.add_argument('-s', '--signed', action='store_true')
    parser.add_argument('-r', '--repeat', )
    parser.add_argument('data', nargs='+')

    return parser

class DebugShell(cmd.Cmd):
    intro = 'ecgc-debug 0.4a\ntype help or ? to list commands\n'
    prompt = '> '
    file = None

    def __init__(self, debugger: UartDebugger) -> None:
        self.__debugger = debugger
        self.__parsers = {
            'read': construct_parser_read(),
            'write': construct_parser_write()
        }

        super().__init__()

    def __print_error(self, error: Exception | str):
        if isinstance(error, Exception):
            print('*** {}: {}'.format(type(error).__name__, str(error)))
        else:
            print('*** {}'.format(error))

    def __parse_args(self, command: str, arg: str) -> Namespace:
        # try parsing arguments
        args = arg.split(' ') if arg else []
        try:
            args = self.__parsers[command].parse_args(args)
        except ArgumentError as e:
            self.__print_error(e)
            return None
        
        return args

    def do_read(self, arg):
        args = self.__parse_args('read', arg)

    def help_read(self):
        self.__parsers['read'].print_help()

    def do_exit(self, arg):
        """Exit the debugging utility"""
        return True

def main_cli():
    parser = ArgumentParser(prog='ecgc-debug', description='Utility for peeking and poking cartridge registers', epilog=__EPILOG, formatter_class=RawTextHelpFormatter)
    parser.add_argument('serial_port', help='Serial port of the programmer')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity of program output')
    parser.add_argument('--version', action='version', version='%(prog)s 0.4a')

    args = parser.parse_args()

    # Configure logging
    logging.addLevelName(OUTPUT_LOG_LEVEL, 'OUTPUT')
    logging.basicConfig(format='%(levelname)8s - %(message)s',
                        level=__LOG_LEVELS[min(args.verbose, len(__LOG_LEVELS) - 1)])

    try:
        with UartDebugger(args.serial_port) as debugger:
            DebugShell(debugger).cmdloop()
    except (DebuggerException, SerialException) as e:
        logging.critical(e)
        log_info(e)
        exit(1)


if __name__ == '__main__':
    main_cli()
