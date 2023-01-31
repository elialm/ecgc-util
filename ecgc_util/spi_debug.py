from __future__ import annotations
import re
from .spi_programmer import SpiProgrammer, scatter


class DebuggerException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class SpiDebugger:
    def __init__(self, port: str) -> None:
        self.__programmer = SpiProgrammer(port)
        self.__enabled = False

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

        self.__programmer.enable()

        # send idle command to check if core is enabled and flush any ongoing transaction
        # last byte must be idle response (0xF1)
        self.__send_packet('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F', r'[0-9A-F]{34}F1', 'initialisation')

        self.__enabled = True

    def disable_core(self) -> None:
        if not self.__enabled:
            raise DebuggerException('debug core is already disabled')

        self.__programmer.disable()
        self.__enabled = False

    def set_address(self, address: int) -> None:
        self.__assert_enabled(self.set_address.__name__)
        if address < 0 or address > 65535:
            raise ValueError(
                'address must be a 16-bit unsigned integer (0-65535)')

        hex_string = '%04X' % address
        addr_low = hex_string[2:4]
        addr_high = hex_string[0:2]

        self.__send_packet('030F', r'F131', 'set high address command')
        self.__send_packet(addr_high + '0F', r'00' + addr_high, 'set high address')
        self.__send_packet('020F', r'F121', 'set low address command')
        self.__send_packet(addr_low + '0F', r'00' + addr_low, 'set low address')

    def enable_auto_increment(self) -> None:
        self.__assert_enabled(self.enable_auto_increment.__name__)
        self.__send_packet('040F', r'F141', 'enable auto increment command')

    def disable_auto_increment(self) -> None:
        self.__assert_enabled(self.enable_auto_increment.__name__)
        self.__send_packet('050F', r'F151', 'disable auto increment command')

    def write(self, data: bytes) -> None:
        for chunk in scatter(data, 16):
            if len(chunk) == 16:
                # Send with burst write
                self.__send_packet('0B0F', r'F1B1', 'write burst command')

                first_byte = '00'
                for burst in scatter(data.hex().upper(), 16):
                    self.__send_packet(burst, first_byte + burst[:-2], 'write burst data')
                    first_byte = burst[-2:]

                self.__send_packet('0F0F', first_byte + r'F1', 'write burst close off')
            else:
                # Send with normal writes
                for byte in chunk:
                    hex_string = '%02X' % byte

                    self.__send_packet('090F', r'F191', 'write command')
                    self.__send_packet(hex_string + '0F', r'00' + hex_string, 'write data')

    def read(self, read_length: int) -> bytes:
        entire_read = bytearray()

        for offset in range(0, read_length, 16):
            upper_bound = min(offset + 16, read_length)
            length = upper_bound - offset

            if length == 16:
                # Receive with burst read
                self.__send_packet('0A0F', r'F1A1', 'read burst command')
                response = self.__send_packet('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F', r'([0-9A-F]{32})00', 'read burst data')
                entire_read += bytes.fromhex(response.group(1))
            else:
                # Receive with normal read
                for _ in range(length):
                    self.__send_packet('080F', r'F181', 'read command')
                    response = self.__send_packet('0F0F', r'([0-9A-F]{2})00', 'read data')
                    entire_read += bytes.fromhex(response.group(1))

        return bytes(entire_read)



    def __send_packet(self, data: str, response_format: re.Pattern | str, exception_info: str = None) -> re.Match:
        if isinstance(response_format, str):
            response_format = re.compile(response_format)

        byte_data = bytes.fromhex(data)
        response = self.__programmer.write(byte_data).hex().upper()

        res = re.match(response_format, response)
        if not res:
            raise DebuggerException('unexpected debugger response{}: expected \"{}\", got \"{}\"'.format(
                ' during ' + exception_info if exception_info else '', response_format, response))

        return res

    def __assert_enabled(self, exception_info: str = None) -> None:
        if not self.__enabled:
            raise DebuggerException('debug core must be enabled for {}operation'.format(
                exception_info + ' ' if exception_info else ''))
