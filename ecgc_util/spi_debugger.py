from __future__ import annotations
from typing import Iterator, Iterable
from serial import SerialException
import re
import logging
import serial

DEBUGGER_BAUD_RATE = 115200
DEBUGGER_DATA_BITS = 8
DEBUGGER_PARITY = serial.PARITY_NONE
DEBUGGER_STOP_BITS = 1

def scatter(collection: Iterable, chunk_size: int) -> Iterator[Iterable]:
    if chunk_size < 1:
        raise ValueError('chunk_size must be 1 or higher')

    for i in range(0, len(collection), chunk_size):
        upper_bound = min(i + chunk_size, len(collection))
        yield collection[i:upper_bound]


class DebuggerException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class SpiDebugger:
    def __init__(self, port: str) -> None:
        self.__enabled = False
        self.__port = serial.Serial(port,
                                    baudrate=DEBUGGER_BAUD_RATE,
                                    bytesize=DEBUGGER_DATA_BITS,
                                    parity=DEBUGGER_PARITY,
                                    stopbits=DEBUGGER_STOP_BITS,
                                    timeout=5)

        # Wait till the programmer is ready
        self.__match_response(r'RDY')
        self.__port.timeout = 0.2

        with self:
            # Disable auto increment by default since it might still be enabled
            self.disable_auto_increment()

            # Set address to 0 since it might be something else
            self.set_address(0)

    def __enter__(self) -> SpiDebugger:
        self.enable_core()
        return self

    def __exit__(self, type, value, traceback) -> bool:
        self.disable_core()
        return value == None

    def is_enabled(self) -> bool:
        return self.__enabled

    def enable_core(self) -> None:
        if self.__enabled:
            raise DebuggerException('debug core is already enabled')

        # TODO: implement

        self.__enabled = True

    def disable_core(self) -> None:
        if not self.__enabled:
            raise DebuggerException('debug core is already disabled')

        # TODO: implement

        self.__enabled = False

    def set_address(self, address: int) -> None:
        self.__assert_enabled(self.set_address.__name__)
        if address < 0 or address > 65535:
            raise ValueError(
                'address must be a 16-bit unsigned integer (0-65535)')

        # TODO: implement

    def enable_auto_increment(self) -> None:
        self.__assert_enabled(self.enable_auto_increment.__name__)

        # TODO: implement

    def disable_auto_increment(self) -> None:
        self.__assert_enabled(self.enable_auto_increment.__name__)

        # TODO: implement

    def write(self, data: bytes) -> None:
        self.__assert_enabled(self.write.__name__)
        
        # TODO: implement

    def read(self, read_length: int) -> bytes:
        self.__assert_enabled(self.read.__name__)

        # TODO: implement

    def __send_packet(self, packet: str, response_format: re.Pattern | str, description: str) -> re.Match:
        self.__port.write(packet.encode('ascii'))
        response = self.__read_response()

        logging.debug('__send_packet() call for \"{}\"'.format(description))
        logging.debug('       sent {}'.format(packet))
        logging.debug('   received {}'.format(response))
        logging.debug('   expected {}'.format(response_format.pattern))

        res = re.match(response_format, response)
        if not res:
            raise DebuggerException('unexpected debugger response during {}: expected \"{}\", got \"{}\"'.format(
                description, response_format.pattern, response))

        return res

    def __read_response(self) -> str:
        read_bytes = self.__port.read_until(b'\n')
        
        if len(read_bytes) == 0:
            raise DebuggerException('serial read returned 0 bytes')

        if read_bytes[-1] != b'\n'[0]:
            raise DebuggerException('read response is not in expected packet form')

        return read_bytes[:-1].decode('ascii')

    def __match_response(self, expected) -> re.Match:
        response = self.__read_response()

        res = re.match(expected, response)
        if not res:
            raise DebuggerException(
                'unexpected response: expected \"{}\", got \"{}\"'.format(expected, response))

        return res

    def __assert_enabled(self, exception_info: str = None) -> None:
        if not self.__enabled:
            raise DebuggerException('debug core must be enabled for {}operation'.format(
                exception_info + ' ' if exception_info else ''))
