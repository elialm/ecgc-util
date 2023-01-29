from __future__ import annotations
import serial
import re
from time import sleep

PROGRAMMER_BAUD_RATE = 115200
PROGRAMMER_DATA_BITS = 8
PROGRAMMER_PARITY = serial.PARITY_NONE
PROGRAMMER_STOP_BITS = 1

PACKAGE_CONTENTS_PATTERN = re.compile(r'#(.+);')


class ProgrammerException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class SpiProgrammer:
    def __init__(self, port: str) -> None:
        self.__port = serial.Serial(port,
                                    baudrate=PROGRAMMER_BAUD_RATE,
                                    bytesize=PROGRAMMER_DATA_BITS,
                                    parity=PROGRAMMER_PARITY,
                                    stopbits=PROGRAMMER_STOP_BITS,
                                    timeout=1)

        # Sleep for a bit to let the Arduino reset
        sleep(2)

        # Disable debug preemptively, since it might still be on
        self.disable()

    def write(self, data: bytes) -> None:
        pass

    def enable(self) -> SpiProgrammer:
        self.__port.write(b'#E;')
        self.__match_response(r'SUCCESS')

        return self

    def disable(self) -> SpiProgrammer:
        self.__port.write(b'#D;')
        self.__match_response(r'SUCCESS')

        return self

    def __read_response(self, expected_length: int) -> None:
        read_bytes = self.__port.read(expected_length)
        if len(read_bytes) != expected_length:
            raise ProgrammerException('unexpected response length: expected {}, got {}'.format(
                expected_length, len(read_bytes)))

        res = re.match(PACKAGE_CONTENTS_PATTERN, read_bytes.decode('ascii'))
        if not res:
            raise ProgrammerException('response is not in proper package form')

        return res.group(1)

    def __match_response(self, expected) -> re.Match:
        response = self.__read_response(len(expected))

        res = re.match(expected, response)
        if not res:
            raise ProgrammerException(
                'unexpected response: expected \"{}\", got \"{}\"'.format(expected, response))

        return res
