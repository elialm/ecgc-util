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
        return f'error responding to CMD{self.sd_cmd} with arg 0x{self.sd_arg:08X}: received {" ".join([hex(b).upper().replace("X", "x") for b in self.sd_response_raw])}'


class SDResponseType(Enum):
    """Enumeration of all SPI responses of the SD card"""

    R1 = auto()
    R1B = auto()
    R2 = auto()
    R3 = auto()
    R7 = auto()


__SD_COMMAND_EXPECTED_RESPONSES = {
    0: SDResponseType.R1,
    1: SDResponseType.R1,
    6: SDResponseType.R1,
    8: SDResponseType.R7,
    9: SDResponseType.R1,
    10: SDResponseType.R1,
    12: SDResponseType.R1B,
    13: SDResponseType.R2,
    16: SDResponseType.R1,
    17: SDResponseType.R1,
    18: SDResponseType.R1,
    24: SDResponseType.R1,
    25: SDResponseType.R1,
    27: SDResponseType.R1,
    28: SDResponseType.R1B,
    29: SDResponseType.R1B,
    30: SDResponseType.R1,
    32: SDResponseType.R1,
    33: SDResponseType.R1,
    38: SDResponseType.R1B,
    42: SDResponseType.R1,
    55: SDResponseType.R1,
    56: SDResponseType.R1,
    58: SDResponseType.R3,
    59: SDResponseType.R1,
}


def sd_command_get_expected_response(cmd_index: int) -> SDResponseType:
    expected_response = __SD_COMMAND_EXPECTED_RESPONSES.get(cmd_index, None)
    if cmd_index == None:
        raise ValueError(
            'given cmd_index does not belong to a valid SD command in SPI mode')

    return expected_response


class SDResponse:
    """Class containing the fields of SD SPI response R1"""

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
        self.raw_r1 = response
        self.r1_parameter_error = bool(response & 0b01000000)
        self.r1_address_error = bool(response & 0b00100000)
        self.r1_erase_sequence_error = bool(response & 0b00010000)
        self.r1_com_crc_error = bool(response & 0b00001000)
        self.r1_illegal_command = bool(response & 0b00000100)
        self.r1_erase_reset = bool(response & 0b00000010)
        self.r1_in_idle_state = bool(response & 0b00000001)

        self.response_type = SDResponseType.R1

    def error_occurred(self) -> bool:
        return self.r1_parameter_error or self.r1_address_error or self.r1_erase_sequence_error or self.r1_com_crc_error or self.r1_illegal_command or self.r1_erase_reset
    

class SDResponseR1B(SDResponse):
    """Class containing the fields of SD SPI response R1b"""

    def __init__(self, r1: SDResponse, extra_data: bytes) -> None:
        """Extend SD response with R1b fields

        Args:
            r1 (SDResponse): base R1 response
            extra_data (bytes): extra data of the R1b response
        """

        super().__init__(r1.raw_r1)

        self.r1b_busy = any(map(lambda d: d == 0, extra_data))
        self.response_type = SDResponseType.R1B


class SDResponseR2(SDResponse):
    """Class containing the fields of SD SPI response R2"""

    def __init__(self, r1: SDResponse, extra_data: bytes) -> None:
        """Extend SD response with R2 fields

        Args:
            r1 (SDResponse): base R1 response
            extra_data (bytes): extra data of the R2 response

        Raises:
            ValueError: if the supplied extra_data is of incorrect length
        """

        super().__init__(r1.raw_r1)

        if len(extra_data) != 1:
            raise ValueError(
                f'expected 1 byte of extra data decoding R2, got {len(extra_data)}')

        # decode R2 byte
        response = extra_data[0]
        self.r2_out_of_range_or_csd_overwrite = bool(response & 0b10000000)
        self.r2_erase_param = bool(response & 0b01000000)
        self.r2_wp_violation = bool(response & 0b00100000)
        self.r2_card_ecc_failed = bool(response & 0b00010000)
        self.r2_cc_error = bool(response & 0b00001000)
        self.r2_error = bool(response & 0b00000100)
        self.r2_wp_erase_skip_or_lock_unlock_cmd_failed = bool(response & 0b00000010)
        self.r2_card_is_locked = bool(response & 0b00000001)

        self.response_type = SDResponseType.R2

    def error_occurred(self) -> bool:
        if super().error_occurred():
            return True
    
        return self.r2_out_of_range_or_csd_overwrite or self.r2_erase_param or self.r2_wp_violation or self.r2_card_ecc_failed or self.r2_cc_error or self.r2_error or self.r2_wp_erase_skip_or_lock_unlock_cmd_failed or self.r2_card_is_locked


class SDResponseR3(SDResponse):
    """Class containing the fields of SD SPI response R3"""

    __VDD_RANGE_BOUNDS = [
        2.7,
        2.8,
        2.9,
        3.0,
        3.1,
        3.2,
        3.3,
        3.4,
        3.5,
        3.6,
    ]

    def __init__(self, r1: SDResponse, extra_data: bytes) -> None:
        """Extend SD response with R3 fields

        Args:
            r1 (SDResponse): base R1 response
            extra_data (bytes): extra data of the R3 response

        Raises:
            ValueError: if the supplied extra_data is of incorrect length
        """

        super().__init__(r1.raw_r1)

        if len(extra_data) != 4:
            raise ValueError(
                f'expected 4 bytes of extra data decoding R3, got {len(extra_data)}')

        # decode R3 bytes
        self.raw_ocr = int.from_bytes(extra_data, 'big')
        self.r3_low_vdd_range = bool(self.raw_ocr & (1 << 7))
        self.r3_s19a = bool(self.raw_ocr & (1 << 24))
        self.r3_co2t = bool(self.raw_ocr & (1 << 27))
        self.r3_uhs2_status = bool(self.raw_ocr & (1 << 29))
        self.r3_ccs = bool(self.raw_ocr & (1 << 30))
        self.r3_busy = not bool(self.raw_ocr & (1 << 31))
        self.r3_vdd_range = self.__decode_vdd_range((self.raw_ocr >> 15) & 0x1FF)

        self.response_type = SDResponseType.R3

    def __decode_vdd_range(self, vdd_range: int) -> tuple[float, float]:
        # get lower bound
        for i in range(9):
            lower_bound = SDResponseR3.__VDD_RANGE_BOUNDS[i]
            if vdd_range & (1 << i):
                break

        # get upper bound
        for i in range(9, 0, -1):
            upper_bound = SDResponseR3.__VDD_RANGE_BOUNDS[i]
            if vdd_range & (1 << i):
                break

        # sanity check on the voltage range
        if lower_bound > upper_bound:
            raise ValueError('invalid voltage range')

        return (lower_bound, upper_bound)
    

class SDResponseR7VoltageAccepted(Enum):
    FROM_2V7_TO_3V6 = auto()
    LOW_VOLTAGE_RANGE = auto()
    RESERVED = auto()
    NOT_DEFINED = auto()

    def from_raw_response(response: int) -> SDResponseR7VoltageAccepted:
        """Get correct SDResponseR7VoltageAccepted from raw R7 response

        Args:
            response (int): raw R7 response

        Returns:
            SDResponseR7VoltageAccepted: interpreted voltage accepted
        """

        voltage_accepted = (response >> 8) & 0xF
        match voltage_accepted:
            case 0b0000:
                return SDResponseR7VoltageAccepted.NOT_DEFINED
            case 0b0001:
                return SDResponseR7VoltageAccepted.FROM_2V7_TO_3V6
            case 0b0010:
                return SDResponseR7VoltageAccepted.LOW_VOLTAGE_RANGE
            case 0b0100:
                return SDResponseR7VoltageAccepted.RESERVED
            case 0b1000:
                return SDResponseR7VoltageAccepted.RESERVED
            case _:
                return SDResponseR7VoltageAccepted.NOT_DEFINED

class SDResponseR7(SDResponse):
    """Class containing the fields of SD SPI response R7"""

    def __init__(self, r1: SDResponse, extra_data: bytes) -> None:
        """Extend SD response with R7 fields

        Args:
            r1 (SDResponse): base R1 response
            extra_data (bytes): extra data of the R7 response

        Raises:
            ValueError: if the supplied extra_data is of incorrect length
        """

        super().__init__(r1.raw_r1)

        if len(extra_data) != 4:
            raise ValueError(
                f'expected 4 bytes of extra data decoding R7, got {len(extra_data)}')

        # decode R7 bytes
        self.raw_r7 = int.from_bytes(extra_data, 'big')
        self.r7_command_version = (self.raw_r7 >> 28) & 0xF
        self.r7_voltage_accepted = SDResponseR7VoltageAccepted.from_raw_response(self.raw_r7)
        self.r7_check_pattern = self.raw_r7 & 0xFF

        self.response_type = SDResponseType.R7
