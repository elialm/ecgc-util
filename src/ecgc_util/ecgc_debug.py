from .exception_debugging import log_info
from .ecgc_debugger import ECGCDebugger, SpiChipSelect, DebuggerException, SerialException, SDResponseType, SDException
from .util import parse_rgbds_int, scatter
from typing import Iterable
from argparse import ArgumentParser, RawTextHelpFormatter, ArgumentError, Namespace
from itertools import chain
from functools import reduce
from pprint import pprint
import logging
import cmd
import inspect


OUTPUT_LOG_LEVEL = 100
__LOG_LEVELS = (
    logging.WARNING,
    logging.INFO,
    logging.DEBUG
)

__READ_EPILOG = """
The read command reads from the specified address. An optional size parameter
can be passed to specify how many bytes are to be read. By default, the size
will be 1.

When reading multiple bytes, the address will be incremented at each received
byte. To disable this behaviour and fix the address at the given value, add
the -f/--fixed flag.

A couple of examples using the read command:
    - Read a single byte from address $4000
        > read $4000
    - Read 16 bytes from addresses $0100-$01FF
        > read $0100 -s 16
    - Read 256 bytes from address $A100
        > read $A100 -f -s 256
"""

__WRITE_EPILOG = """
The write command writes the given data to the specified address. When writing
multiple bytes, the address will be incremented at each received byte. To
disable this behaviour and fix the address at the given value, add the
-f/--fixed flag.

The data is given as a series of bytes separated by a space. Each value must
fit within an 8-bit unsigned integer.

Data can also be given as a repeated pattern. When specifying the -r/--repeat
flag, one can give a number TIMES which repeats the given data pattern TIMES
times.

A couple of examples using the write command:
    - Write a single byte to address $4000
        > write $4000 $FF
    - Write the numbers 1-16 to addresses $0100-$01FF
        > write $0100 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
    - Write 4 bytes of data to address $A100
        > write $A100 -f $DE $AD $BE $EF
    - Write $00 to addresses $4000-$7FFF
        > write $4000 -r $4000 $00
"""

__SPI_EPILOG = """
The spi command writes the given data over SPI to the selected device. The
device can be selected using the cs parameter. By default, the CS pin of the
given peripheral is asserted on submission of the command and deasserted upon
completion. CS can be kept asserted using the -k/--keep-selected flag.

The data is given as a series of bytes separated by a space. Each value must
fit within an 8-bit unsigned integer.

Data can also be given as a repeated pattern. When specifying the -r/--repeat
flag, one can give a number TIMES which repeats the given data pattern TIMES
times.

A couple of examples using the spi command:
    - Read flash unique ID
        > spi flash $4B $00 $00 $00 $00 -k
        > spi flash -r 16 $00
"""

__SD_EPILOG ="""
The sd command send the given command to the SD card and reads back the response
(depends on the given command). CS assertion is done automatically in this process,
but like the spi command can be kept selected using the -k/--keep-selected flag.

The command is specified using its command index and argument. These are given as
arguments to the sd command. Using this information, the script will build the
command frame. Its CRC will also be calculated and appended to the cmd frame.

The expected response can be passed using the -r/--expected-response flag. If
none is given, only the SD card's R1 response is expected.

A couple of examples using the sd command:
    - Resetting the card with CMD0
        > sd 0 0

WARNING: familiarity with the SD card SPI protocol is recommended when using this
command. Misuse could result in corrupted data or destroying the SD card.
"""

__EPILOG = f"""
The utility will open a command prompt for entering commands. Usable commands
are documented below. These commands give the user the ability to peek and poke
at registers inside the cartridge's memory space.

Do note that the DMA registers are NOT accessible through the debug core due to
the firmware architecture.

Also note that all address operations must occur with the address range of
0x0000-0xFFFF. Any operations outside this range will raise an error and be
cancelled.

## Available commands

    - read [-f] [-s SIZE] address
    - write [-f] [-s] [-r REPEAT] address data [data ...]
    - spi [-r REPEAT] [-k] {{flash,rtc,sd}} data [data ...]
    - sd ...

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

{__READ_EPILOG}

## Write command

{__WRITE_EPILOG}

## Spi command

{__SPI_EPILOG}

## Sd command

{__SD_EPILOG}
"""


class CommandError(Exception):
    pass

class SubArgumentParser(ArgumentParser):
    def error(self, message):
        raise ArgumentError(None, message)


def construct_parser_read() -> SubArgumentParser:
    parser = SubArgumentParser(prog='read', epilog=__READ_EPILOG, formatter_class=RawTextHelpFormatter, add_help=False, exit_on_error=False)
    parser.add_argument('address', help='address to read from')
    parser.add_argument('-f', '--fixed', action='store_true', help='disable address increment on multi-byte operations')
    parser.add_argument('-s', '--size', default='1', help='number of bytes to read. defaults to 1')

    return parser

def construct_parser_write() -> SubArgumentParser:
    parser = SubArgumentParser(prog='write', epilog=__WRITE_EPILOG, formatter_class=RawTextHelpFormatter, add_help=False, exit_on_error=False)
    parser.add_argument('address', help='address to write to')
    parser.add_argument('data', nargs='+', help='data to be written')
    parser.add_argument('-f', '--fixed', action='store_true', help='disable address increment on multi-byte operations')
    parser.add_argument('-r', '--repeat', default='1', help='repeat the given data for the specified number of times')

    return parser

def construct_parser_spi() -> SubArgumentParser:
    parser = SubArgumentParser(prog='spi', epilog=__SPI_EPILOG, formatter_class=RawTextHelpFormatter, add_help=False, exit_on_error=False)
    parser.add_argument('cs', choices=('flash', 'rtc', 'sd', 'none'), help='SPI peripheral to select from the choices available')
    parser.add_argument('data', nargs='+', help='data to be written')
    parser.add_argument('-k', '--keep-selected', action='store_true', help='keep the CS pin asserted after command completion')
    parser.add_argument('-r', '--repeat', default='1', help='repeat the given data for the specified number of times')

    return parser

def construct_parser_sd() -> SubArgumentParser:
    parser = SubArgumentParser(prog='sd', epilog=__SD_EPILOG, formatter_class=RawTextHelpFormatter, add_help=False, exit_on_error=False)
    parser.add_argument('cmd', help='command index of SD command')
    parser.add_argument('arg', help='argument of SD command')
    parser.add_argument('-k', '--keep-selected', action='store_true', help='keep the SD card selected after command completion')

    return parser


class DebugShell(cmd.Cmd):
    intro = 'ecgc-debug 0.4a\ntype help or ? to list commands\n'
    prompt = '> '
    file = None

    def __init__(self, debugger: ECGCDebugger) -> None:
        super().__init__()
        self.__debugger = debugger
        self.__parsers = {
            'read': construct_parser_read(),
            'write': construct_parser_write(),
            'spi': construct_parser_spi(),
            'sd': construct_parser_sd()
        }

    def __print_error(self, error: Exception | str):
        if isinstance(error, Exception):
            print('*** {}: {}'.format(type(error).__name__, str(error)))
        else:
            print('*** {}'.format(error))

    def __parse_args(self, command: str, arg: str) -> Namespace:
        # try parsing arguments
        args = arg.split(' ') if arg else []
        args = self.__parsers[command].parse_args(args)
        return args
    
    def __check_address_and_size(self, address: int, size: int, fixed_address: bool):
        if address < 0 or address > 0xFFFF:
            raise ValueError('address must be a 16-bit unsigned integer')
        
        if size < 0 or size > 0xFFFF:
            raise ValueError('size must be a 16-bit unsigned integer')
        
        if not fixed_address and address + size > 0x10000:
            raise ValueError('given parameters result in operations done outside the cartridge\'s memory map')

    def __decode_ascii(self, c: int, default: str = '?') -> str:
        return chr(c) if c != None and c > 0x1F and c < 0x7F else default

    def __hexdump(self, start_address: int, data: bytes) -> Iterable[str]:
        # scatter data into 16 long blocks
        aligned_address = start_address - (start_address % 16)
        first_block_len = 16 - (start_address - aligned_address)
        scattered_data = [ data[:first_block_len] ]
        scattered_data.extend(scatter(data[first_block_len:], 16))

        # convert bytes() objects into int arrays
        for i, block in enumerate(scattered_data):
            scattered_data[i] = [ b for b in block ]

        # pad first (if necessary)
        if len(scattered_data[0]) != 16:
            # if misaligned, add padding to the left till aligned
            if aligned_address != start_address:
                padding_amount = start_address - aligned_address
                scattered_data[0] = [ None for _ in range(padding_amount) ] + scattered_data[0]
            
            # if still not full length, pad to the right till it is
            if len(scattered_data[0]) != 16:
                padding_amount = 16 - len(scattered_data[0])
                scattered_data[0] = scattered_data[0] + [ None for _ in range(padding_amount) ]

        # pad last block (if necessary)
        if len(scattered_data[-1]) != 16:
            padding = [ None for _ in range(16 - len(scattered_data[-1])) ]
            scattered_data[-1] = scattered_data[-1] + padding

        # print output into lines
        lines = []
        for i, block in enumerate(scattered_data):
            line = f'{aligned_address + (i * 16):04X}  '
            for sub_block in scatter(block, 8):
                line += ' '.join('--' if b == None else f'{b:02X}' for b in sub_block) + '   '
            line += '|{}|'.format(''.join(self.__decode_ascii(b, '.') for b in block))
            lines.append(line)

        return lines
    
    def __parse_uint8(self, val_str: str) -> int:
        val = parse_rgbds_int(val_str)

        if val < 0 or val > 0xFF:
            raise ValueError(f'value \"{val_str}\" is not a valid 8-bit unsigned integer')
        
        return val
    
    def __extend_bytearray(array: bytearray, data: bytes) -> bytearray:
        array.extend(data)
        return array

    def do_read(self, arg):
        # parse and sanitise arguments
        try:
            args = self.__parse_args('read', arg)
            args.address = parse_rgbds_int(args.address)
            args.size = parse_rgbds_int(args.size)
            self.__check_address_and_size(args.address, args.size, args.fixed)
        except (ArgumentError, ValueError) as e:
            self.__print_error(e)
            return

        # perform the read
        self.__debugger.set_auto_increment(not args.fixed)
        self.__debugger.set_address(args.address)
        read_data = self.__debugger.read(args.size)

        # print read data
        for line in self.__hexdump(0 if args.fixed else args.address, read_data):
            print(line)

    def help_read(self):
        self.__parsers['read'].print_help()

    def do_write(self, arg):
        # parse and sanitise arguments
        try:
            args = self.__parse_args('write', arg)
            args.address = parse_rgbds_int(args.address)
            args.data = bytes([ self.__parse_uint8(b) for b in args.data ])
            args.repeat = parse_rgbds_int(args.repeat)
            if args.repeat < 1:
                raise ValueError('repeat parameter must be a non-zero positive integer')
            self.__check_address_and_size(args.address, len(args.data) * args.repeat, args.fixed)
        except (ArgumentError, ValueError) as e:
            self.__print_error(e)
            return

        # construct write data using repeat parameter
        write_data = chain(args.data for _ in range(args.repeat))
        write_data = reduce(DebugShell.__extend_bytearray, write_data, bytearray())

        # perform the write
        self.__debugger.set_auto_increment(not args.fixed)
        self.__debugger.set_address(args.address)
        self.__debugger.write(write_data)

    def help_write(self):
        self.__parsers['write'].print_help()

    def do_spi(self, arg):
        # parse and sanitise arguments
        try:
            args = self.__parse_args('spi', arg)
            args.data = [ self.__parse_uint8(b) for b in args.data ]
            args.repeat = parse_rgbds_int(args.repeat)
            if args.repeat < 1:
                raise ValueError('repeat parameter must be a non-zero positive integer')
            args.cs = SpiChipSelect.__members__.get(args.cs.upper(), None)
            if not args.cs:
                raise ValueError('cs is not one of the given choices')
        except (ArgumentError, ValueError) as e:
            self.__print_error(e)
            return
        
        # construct write data using repeat parameter
        write_data = chain(args.data for _ in range(args.repeat))
        write_data = reduce(DebugShell.__extend_bytearray, write_data, bytearray())

        # perform the SPI writes
        self.__debugger.spi_select(args.cs)
        read_data = self.__debugger.spi_write_read(write_data)

        # check if cs needs to be released
        if not args.keep_selected:
            self.__debugger.spi_deselect()

        # print read data
        write_lines = self.__hexdump(0, write_data)
        read_lines = self.__hexdump(0, read_data)
        for wline, rline in zip(write_lines, read_lines):
            print(wline)
            print(rline)
            print()

    def help_spi(self):
        self.__parsers['spi'].print_help()

    def do_sd(self, arg):
        # parse and sanitise arguments
        try:
            args = self.__parse_args('sd', arg)
            args.cmd = parse_rgbds_int(args.cmd)
            if args.cmd < 0 or args.cmd > 0x3F:
                raise ValueError('cmd must be a 6-bit unsigned integer')
            args.arg = parse_rgbds_int(args.arg)
            if args.arg < 0 or args.arg > 0xFFFFFFFF:
                raise ValueError('arg must be a 32-bit unsigned integer')
        except (ArgumentError, ValueError) as e:
            self.__print_error(e)
            return
        
        # send command
        try:
            response = self.__debugger.sd_send_cmd(args.cmd, args.arg, args.expected_response, args.keep_selected)
        except (SDException, NotImplementedError) as e:
            self.__print_error(e)
            return
        
        # TODO: properly print response
        pprint(inspect.getmembers(response))

    def help_sd(self):
        self.__parsers['sd'].print_help()

    def do_exit(self, arg):
        """Exits the debugging utility"""
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
        with ECGCDebugger(args.serial_port) as debugger:
            DebugShell(debugger).cmdloop()
    except (DebuggerException, SerialException) as e:
        logging.critical(e)
        log_info(e)
        exit(1)


if __name__ == '__main__':
    main_cli()
