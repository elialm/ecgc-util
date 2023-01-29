from __future__ import annotations
from .spi_programmer import SpiProgrammer, ProgrammerException, SerialException

class SpiDebugCore:
    def __init__(self, port: str) -> None:
        self.__programmer = SpiProgrammer(port)
        self.__enabled = False

    def enable_core(self) -> SpiDebugCore:
        return self

    def disable_core(self) -> SpiDebugCore:
        return self

    def set_address(self, address: int) -> SpiDebugCore:
        return self

    def enable_auto_increment(self) -> SpiDebugCore:
        return self

    def disable_auto_increment(self) -> SpiDebugCore:
        return self

    def write(self, data: bytes) -> SpiDebugCore:
        return self

    def read(self, length: int) -> bytes:
        return self