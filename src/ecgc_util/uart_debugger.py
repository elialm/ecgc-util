from __future__ import annotations
from .debugger_exception import DebuggerException
from .util import scatter
from serial import SerialException
import logging
import serial
import re
from time import sleep

DEBUGGER_BAUD_RATE = 115200
DEBUGGER_DATA_BITS = 8
DEBUGGER_PARITY = serial.PARITY_NONE
DEBUGGER_STOP_BITS = 1

CONFIG_REG_DBG_EN = 0b00010000
CONFIG_REG_AUTO_INC = 0b00100000

class UartDebugger:
    """Class for controlling the uart_debug core inside the cartridge"""

    def __init__(self, port: str) -> None:
        """Create UartDebugger instance

        Args:
            port (str): serial port of the programmer to operate

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
                                    timeout=0.2)
        
        # Flush any ongoing operations
        self.__send_packet(bytes(258), r'\x01$', 258, 'initial flush')

        # Clear configuration register for operation in a defined state
        # This also disabled the core
        self.__config_reg_write(0)

        # Perform other initialisations
        self.__set_address(0)

    def __enter__(self) -> UartDebugger:
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

        self.__enable_core()

    def disable_core(self) -> None:
        """Disable the cartridge's debug core

        Raises:
            DebuggerException: if the core is already disabled or an
            unexpected response is received
            SerialException: if some communication error occurs
        """

        if not self.__enabled:
            raise DebuggerException('debug core is already disabled')

        self.__disable_core()

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
        self.__set_address(address)

    def set_auto_increment(self, val: bool) -> None:
        """Enable/disable auto increment feature based on given value

        Args:
            val (bool): true = enable, false = disable
        """

        self.__assert_enabled(self.set_auto_increment.__name__)
        self.__set_auto_increment(val)

    def enable_auto_increment(self) -> None:
        """Enable the debug core's auto increment feature"""

        self.__assert_enabled(self.enable_auto_increment.__name__)
        self.__enable_auto_increment()

    def disable_auto_increment(self) -> None:
        """Disable the debug core's auto increment feature"""
        
        self.__assert_enabled(self.disable_auto_increment.__name__)
        self.__disable_auto_increment()

    def write(self, data: bytes | int) -> None:
        """Write a sequence of bytes to the cartridge

        Args:
            data (bytes|int): data to write to the cartridge. In case of an int, only the LSB is written.

        Raises:
            DebuggerException: if the core is already disabled or an
            unexpected response is received
            SerialException: if some communication error occurs
        """

        self.__assert_enabled(self.write.__name__)
        self.__write(data)

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
        return self.__read(read_length)
    
    def __enable_core(self) -> None:
        val = self.__config_reg_read()
        self.__config_reg_write(val | CONFIG_REG_DBG_EN)
        self.__enabled = True

    def __disable_core(self) -> None:
        val = self.__config_reg_read()
        self.__config_reg_write(val & ~CONFIG_REG_DBG_EN)
        self.__enabled = False

    def __set_address(self, address: int) -> None:
        if address < 0 or address > 65535:
            raise ValueError(
                'address must be a 16-bit unsigned integer (0-65535)')
        
        packet = bytearray(b'\x10')
        packet.extend(address.to_bytes(2, 'little'))
        expected = r'\x11' + UartDebugger.__bytes_to_regex(address.to_bytes(2, 'little'))

        self.__send_packet(packet, expected, 3, 'set address')

    def __set_auto_increment(self, val: bool) -> None:
        reg = self.__config_reg_read()

        if val:
            self.__config_reg_write(reg | CONFIG_REG_AUTO_INC)
        else:
            self.__config_reg_write(reg & ~CONFIG_REG_AUTO_INC)

    def __enable_auto_increment(self) -> None:
        self.__set_auto_increment(True)

    def __disable_auto_increment(self) -> None:
        self.__set_auto_increment(False)

    def __write(self, data: bytes | int) -> None:
        if type(data) == int:
            data = data.to_bytes(1, 'little')

        for write_burst in scatter(data, 256):
            packet = bytearray(b'\x30')
            packet.append(len(write_burst) - 1)
            packet.extend(write_burst)
            expected = r'\x31' + '\\x{:02x}'.format(len(write_burst) - 1) + UartDebugger.__bytes_to_regex(write_burst)

            self.__send_packet(packet, expected, len(write_burst) + 2, 'write data')

    def __read(self, read_length: int) -> bytes:
        if read_length < 1:
            raise ValueError('read length must be at least 1')

        entire_read = bytearray()

        for burst_length in map(lambda i: min(read_length - i, 256), range(0, read_length, 256)):
            packet = bytearray(b'\x20')
            packet.append(burst_length - 1)
            expected = '\\x21\\x{:02x}'.format(burst_length - 1)

            # First send read command, then read data into buffer
            self.__send_packet(packet, expected, 2, 'read command')
            entire_read.extend(self.__read_response(burst_length))

        return bytes(entire_read)
    
    def __config_reg_read(self) -> int:
        return self.__send_packet(b'\x02', r'\x03(.)', 2, 'config register read').group(1)[0]
    
    def __config_reg_write(self, value: int) -> None:
        if value < 0 or value > 255:
            raise ValueError('value must be an 8-bit unsigned integer')
        
        packet = bytearray(b'\x04')
        packet.append(value)
        expected = '\\x05\\x{:02x}'.format(value)

        self.__send_packet(packet, expected, 2, 'config register write')

    def __format_bytes(bb: bytes, separator: str = ' ') -> str:
        return separator.join('{:02X}'.format(b) for b in bb)
    
    def __bytes_to_regex(bb: bytes) -> str:
        return ''.join('\\x{:02x}'.format(b) for b in bb)

    def __send_packet(self, packet: bytes, response_format: bytes | str, expected_length: int, description: str = 'unspecified operation') -> re.Match:
        # TODO: temporary fix for lower SPI speeds
        # Ideally, this should only be done when limiting spi write speed
        for b in packet:
            self.__port.write(b.to_bytes(1, 'little'))
            self.__port.flush()
            sleep(0.001)

        # self.__port.write(packet)

        logging.debug('sent data for \"{}\"'.format(description))
        logging.debug('       sent {}'.format(UartDebugger.__format_bytes(packet)))

        # encode into ascii if str type
        if isinstance(response_format, str):
            response_format = response_format.encode('ascii')

        return self.__match_response(response_format, expected_length, description)

    def __read_response(self, expected_length: int) -> bytes:
        read_bytes = self.__port.read(expected_length)
        
        if len(read_bytes) == 0:
            raise DebuggerException('serial read returned 0 bytes')
        
        if len(read_bytes) != expected_length:
            raise DebuggerException('serial read returned {} bytes, expected {}'.format(len(read_bytes), expected_length))

        return read_bytes

    def __match_response(self, expected_pattern: bytes, expected_length: int, description: str) -> re.Match:
        response = self.__read_response(expected_length)

        logging.debug('matching response for \"{}\"'.format(description))
        logging.debug('   expected {}'.format(expected_pattern))
        logging.debug('   received {}'.format(UartDebugger.__format_bytes(response)))

        res = re.search(expected_pattern, response)
        if not res:
            raise DebuggerException(expected_response=expected_pattern, actual_response=response, action_description=description)

        return res

    def __assert_enabled(self, exception_info: str = None) -> None:
        if not self.__enabled:
            raise DebuggerException('debug core must be enabled for {}operation'.format(
                exception_info + ' ' if exception_info else ''))
