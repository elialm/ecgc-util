from __future__ import annotations
import re
from .spi_programmer import SpiProgrammer, ProgrammerException, SerialException


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

    def enable_core(self) -> SpiDebugger:
        if self.__enabled:
            raise DebuggerException('debug core is already enabled')

        self.__programmer.enable()

        # send idle command to check if core is enabled
        # 1st byte can be anything, but 2nd byte must be idle response (0xF1)
        self.__send_packet('0F0F', r'[0-9A-F]{2}F1', 'initialisation error')

        self.__enabled = True
        return self

    def disable_core(self) -> SpiDebugger:
        if not self.__enabled:
            raise DebuggerException('debug core is already disabled')

        self.__programmer.disable()

        self.__enabled = False
        return self

    def set_address(self, address: int) -> SpiDebugger:
        return self

    def enable_auto_increment(self) -> SpiDebugger:
        return self

    def disable_auto_increment(self) -> SpiDebugger:
        return self

    def write(self, data: bytes) -> SpiDebugger:
        return self

    def read(self, length: int) -> bytes:
        return b''

    def __send_packet(self, data: str, response_format: re.Pattern | str, exception_info: str = None) -> re.Match:
        if isinstance(response_format, str):
            response_format = re.compile(response_format)

        byte_data = bytes.fromhex(data)
        response = self.__programmer.write(byte_data).hex().upper()

        res = re.match(response_format, response)
        if not res:
            raise DebuggerException('{}unexpected debugger response: expected \"{}\", got \"{}\"'.format(
                exception_info + ': ' if exception_info else '', response_format, response))

        return res
