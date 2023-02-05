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
    """Scatter an Iterable over multiple Iterables of a max length

    Args:
        collection (Iterable): Iterable to scatter
        chunk_size (int): maximum length of each chunk scattered.
        Must be larger than 1.

    Raises:
        ValueError: if chunk_size is an invalid value

    Yields:
        Iterator[Iterable]: slice after slice with a maximum length
        of chunk_size
    """

    if chunk_size < 1:
        raise ValueError('chunk_size must be 1 or higher')

    for i in range(0, len(collection), chunk_size):
        upper_bound = min(i + chunk_size, len(collection))
        yield collection[i:upper_bound]


class DebuggerException(Exception):
    """Exception thrown when an error occurs during SpiDebugger operations"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class SpiDebugger:
    """Class for controlling an ecgc SPI programmer via a serial port"""

    def __init__(self, port: str) -> None:
        """Create SpiDebugger instance

        Args:
            port (str): serial port of the spi programmer to operate

        Raises:
            DebuggerException: if the core is already enabled or an
            unexpected response is received
            SerialException: if some communication error occurs
        """

        self.__enabled = False
        self.__port = serial.Serial(port,
                                    baudrate=DEBUGGER_BAUD_RATE,
                                    bytesize=DEBUGGER_DATA_BITS,
                                    parity=DEBUGGER_PARITY,
                                    stopbits=DEBUGGER_STOP_BITS,
                                    timeout=5)

        # Wait till the programmer is ready
        self.__match_response(r'RDY', 'initialisation')
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
        """Query whether the core is enabled or not

        Returns:
            bool: indicating the core is enabled or not
        """

        return self.__enabled

    def enable_core(self) -> None:
        """Enable the cartridge's debug core

        Raises:
            DebuggerException: if the core is already enabled or an
            unexpected response is received
            SerialException: if some communication error occurs
        """

        if self.__enabled:
            raise DebuggerException('debug core is already enabled')

        self.__send_packet('CE', r'ACK', 'core enable')
        self.__enabled = True

    def disable_core(self) -> None:
        """Disable the cartridge's debug core

        Raises:
            DebuggerException: if the core is already disabled or an
            unexpected response is received
            SerialException: if some communication error occurs
        """

        if not self.__enabled:
            raise DebuggerException('debug core is already disabled')

        self.__send_packet('CD', r'ACK', 'core disable')
        self.__enabled = False

    def set_address(self, address: int) -> None:
        """Set the debug core's address

        Args:
            address (int): address to be set.
            Must be a 16-bit unsigned integer.

        Raises:
            ValueError: if address is an invalid value
            DebuggerException: if the core is already disabled or an
            unexpected response is received
            SerialException: if some communication error occurs
        """

        self.__assert_enabled(self.set_address.__name__)
        if address < 0 or address > 65535:
            raise ValueError(
                'address must be a 16-bit unsigned integer (0-65535)')

        self.__send_packet('A%04X' % address, r'ACK', 'set address')

    def enable_auto_increment(self) -> None:
        """Enable the debug core's auto increment feature"""

        self.__assert_enabled(self.enable_auto_increment.__name__)
        self.__send_packet('IE', r'ACK', 'enable auto increment')

    def disable_auto_increment(self) -> None:
        """Disable the debug core's auto increment feature"""
        
        self.__assert_enabled(self.enable_auto_increment.__name__)
        self.__send_packet('ID', r'ACK', 'disable auto increment')

    def write(self, data: bytes) -> None:
        """Write a sequence of bytes to the cartridge

        Args:
            data (bytes): data to write to the cartridge

        Raises:
            DebuggerException: if the core is already disabled or an
            unexpected response is received
            SerialException: if some communication error occurs
        """

        self.__assert_enabled(self.write.__name__)
        
        for write_burst in scatter(data, 256):
            self.__send_packet('W%02X' % (len(write_burst) - 1), r'ACK', 'write command')
            for data_burst in scatter(write_burst, 32):
                data_string = 'D' + data_burst.hex().upper()
                self.__send_packet(data_string, r'ACK', 'write data')

    def read(self, read_length: int) -> bytes:
        """Read a sequence of bytes from the cartridge

        Args:
            read_length (int): number of byte to read. Must be 1 or larger.

        Raises:
            ValueError: if read_length is an invalid value
            DebuggerException: if the core is already disabled or an
            unexpected response is received
            SerialException: if some communication error occurs

        Returns:
            bytes: bytes read from the cartridge
        """
        
        self.__assert_enabled(self.read.__name__)
        if read_length < 1:
            raise ValueError('read length must be at least 1')

        entire_read = bytearray()

        for burst_length in map(lambda i: min(read_length - i, 256), range(0, read_length, 256)):
            read_command = 'R%02X' % (burst_length - 1)
            self.__port.write(read_command.encode('ascii') + b'\n')

            logging.debug('sent data for \"read command\"')
            logging.debug('       sent {}'.format(read_command))

            for data_length in map(lambda i: min(burst_length - i, 32), range(0, burst_length, 32)):
                res = self.__match_response(r'D([0-9A-F]{' + str(data_length * 2) + r'})', 'read data')
                entire_read += bytes.fromhex(res.group(1))

        return bytes(entire_read)

    def __send_packet(self, packet: str, response_format: str, description: str) -> re.Match:
        self.__port.write(packet.encode('ascii') + b'\n')

        logging.debug('sent data for \"{}\"'.format(description))
        logging.debug('       sent {}'.format(packet))

        response = self.__read_response()
        res = re.match(response_format, response)

        if not res:
            raise DebuggerException('unexpected debugger response during {}: expected \"{}\", got \"{}\"'.format(
                description, response_format, response))

        return res

    def __read_response(self) -> str:
        read_bytes = self.__port.read_until(b'\n')
        
        if len(read_bytes) == 0:
            raise DebuggerException('serial read returned 0 bytes')

        if read_bytes[-1] != b'\n'[0]:
            raise DebuggerException('read response is not in expected packet form')

        return read_bytes[:-1].decode('ascii')

    def __match_response(self, expected, description) -> re.Match:
        response = self.__read_response()

        logging.debug('matching response for \"{}\"'.format(description))
        logging.debug('   received {}'.format(response))
        logging.debug('   expected {}'.format(expected))

        res = re.match(expected, response)
        if not res:
            raise DebuggerException(
                'unexpected response: expected \"{}\", got \"{}\"'.format(expected, response))

        return res

    def __assert_enabled(self, exception_info: str = None) -> None:
        if not self.__enabled:
            raise DebuggerException('debug core must be enabled for {}operation'.format(
                exception_info + ' ' if exception_info else ''))
