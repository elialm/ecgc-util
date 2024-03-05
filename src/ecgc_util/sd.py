from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass

class SDException(Exception):
    """Exception thrown when an error occurs during SD card operations"""

    def __init__(self, sd_cmd: int, sd_arg: int, sd_response_raw: bytes, sd_response: SDResponse = None, *args: object) -> None:
        super().__init__(*args)

        self.sd_cmd = sd_cmd
        self.sd_arg = sd_arg
        self.sd_response_raw = sd_response_raw
        self.sd_response = sd_response

    def __str__(self) -> str:
        return f'error responding to CMD{self.sd_cmd} with arg 0x{self.sd_arg:08X}: received {"".join([hex(b).upper() for b in self.sd_response_raw])}'


class SDResponseType(Enum):
    """Enumeration of all SPI responses of the SD card"""

    R1 = auto()
    R1B = auto()
    R2 = auto()
    R3 = auto()
    R7 = auto()

class SDResponse:
    """Class containing the fields of SD SPI response R1 and can be extended with longer responses"""

    def __init__(self, response: int) -> None:
        """Construct response object from response byte

        Args:
            response (int): R1 response byte

        Raises:
            ValueError: if response is not an 8-bit unsigned integer
            or an invalid R1 response (MSB != 0)
        """

        if response < 0 or response > 0xFF:
            raise ValueError('response must be an 8-bit unsigned integer')
        
        if response & 0x80:
            raise ValueError('MSB is not low')

        # decoding R1 byte
        self.r1_parameter_error = bool(response & 0b01000000)
        self.r1_address_error = bool(response & 0b00100000)
        self.r1_erase_sequence_error = bool(response & 0b00010000)
        self.r1_com_crc_error = bool(response & 0b00001000)
        self.r1_illegal_command = bool(response & 0b00000100)
        self.r1_erase_reset = bool(response & 0b00000010)
        self.r1_in_idle_state = bool(response & 0b00000001)

        self.response_type = SDResponseType.R1
        self.error_with_r1 = bool(response & 0b01111110)

    def error_occurred(self) -> bool:
        if self.error_with_r1:
            return True
        
        # TODO: handle other response types

        return False

    def __assert_response_type(self):
        if self.response_type != SDResponseType.R1:
            raise ValueError(f'object with response type {self.response_type.name} cannot be extended')

    def extend_with_r2(self, extra_data: bytes):
        """Extend SD response with R2 fields

        Args:
            extra_data (bytes): extra byte containing the content from R2

        Raises:
            ValueError: if object has already been extended
            or extra data is not 1 byte long
        """

        self.__assert_response_type()
        if len(extra_data) != 1:
            raise ValueError(f'expected 1 byte of extra data decoding R2, got {len(extra_data)}')
        
        # decode R2 byte
        response = extra_data[0]
        self.r2_out_of_range_or_csd_overwite = bool(response & 0b10000000)
        self.r2_erase_param = bool(response & 0b01000000)
        self.r2_wp_violation = bool(response & 0b00100000)
        self.r2_card_ecc_failed = bool(response & 0b00010000)
        self.r2_cc_error = bool(response & 0b00001000)
        self.r2_error = bool(response & 0b00000100)
        self.r2_wp_erase_skip_or_lock_unlock_cmd_failed = bool(response & 0b00000010)
        self.r2_card_is_locked = bool(response & 0b00000001)

        self.response_type = SDResponseType.R2
