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

    def write(self, data: bytes) -> bytes:
        entire_response = bytearray()

        for i in range(0, len(data), 8):
            upper_bound = min(i+8, len(data))
            chunk = data[i:upper_bound]
            burst_cmd = '#B{};'.format(chunk.hex().upper()).encode('ascii')

            self.__port.write(burst_cmd)
            response = self.__match_response(r'R([0-9a-fA-F]{' + str(len(chunk) * 2) + r'})', len(chunk) * 2 + 1)
            entire_response += response.group(1).encode('ascii')

        return bytes(entire_response)

    def enable(self) -> None:
        self.__port.write(b'#E;')
        self.__match_response(r'SUCCESS')

    def disable(self) -> None:
        self.__port.write(b'#D;')
        self.__match_response(r'SUCCESS')

    def __read_response(self, expected_length: int) -> str:
        read_bytes = self.__port.read(expected_length)
        if len(read_bytes) != expected_length:
            raise ProgrammerException('unexpected response length: expected {}, got {}'.format(
                expected_length, len(read_bytes)))

        res = re.match(PACKAGE_CONTENTS_PATTERN, read_bytes.decode('ascii'))
        if not res:
            raise ProgrammerException('response is not in proper package form')

        return res.group(1)

    def __match_response(self, expected, length = None) -> re.Match:
        if length == None:
            length = len(expected)

        response = self.__read_response(length + 2)

        res = re.match(expected, response)
        if not res:
            raise ProgrammerException(
                'unexpected response: expected \"{}\", got \"{}\"'.format(expected, response))

        return res
