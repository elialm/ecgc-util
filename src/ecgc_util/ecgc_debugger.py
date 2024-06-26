from __future__ import annotations
from .uart_debugger import UartDebugger, DebuggerException, SerialException
from .sd import SDResponseType, SDException, SDResponse, SDResponseR1B, SDResponseR2, SDResponseR3, SDResponseR7, sd_cmd_get_expected_response, sd_acmd_get_expected_response
from enum import Enum
import logging
from itertools import repeat

class SpiChipSelect(Enum):
    """Enumeration of all the CS targets with their value being the CS register value to select it"""

    FLASH = (0b11111110).to_bytes(1, 'little')
    RTC = (0b11111101).to_bytes(1, 'little')
    SD = (0b11111011).to_bytes(1, 'little')
    NONE = (0b11111111).to_bytes(1, 'little')

class ECGCDebugger(UartDebugger):
    """Class for controlling the ecgc Gen4 cartridge via its uart_debug core, offering more functionality beyond just the debug core"""

    __CART_REG_SPI_BASE = 0xA600
    __CART_REG_SPI_CTRL = __CART_REG_SPI_BASE + 0
    __CART_REG_SPI_FDIV = __CART_REG_SPI_BASE + 1
    __CART_REG_SPI_CS = __CART_REG_SPI_BASE + 2
    __CART_REG_SPI_DATA = __CART_REG_SPI_BASE + 3

    __SPI_DEFAULT_CTRL = 0b00000001
    __SPI_FCLK = 100_000_000
    __SPI_CRC7_POLYNOM = 0b10001001

    def __init__(self, port: str) -> None:
        """Create ECGCDebugger instance

        Args:
            port (str): serial port of the spi programmer to operate

        Raises:
            DebuggerException: if an unexpected response is received
            SerialException: if some communication error occurs
        """

        super().__init__(port)

    def enable_core(self) -> None:
        super().enable_core()
    
        # initialise SPI firmware
        self.disable_auto_increment()
        self.set_address(ECGCDebugger.__CART_REG_SPI_CTRL)
        self.write(ECGCDebugger.__SPI_DEFAULT_CTRL)
        self.spi_deselect()

        # initialise SD with ~400kHz clock with MOSI being high for at least 74 clocks
        self.spi_set_speed(400_000)
        self.spi_write(bytes(repeat(0xFF, 10)))

    def __calculate_fspi(fdiv: int) -> float:
        if fdiv < 0 or fdiv > 0xFF:
            raise ValueError('fdiv must be an 8-bit unsigned integer')
        
        return ECGCDebugger.__SPI_FCLK / (fdiv + 1)
    
    def __calculate_fdiv(fspi: int) -> int:
        return max(min(round((ECGCDebugger.__SPI_FCLK / fspi) - 1), 0xFF), 0)

    def spi_set_speed(self, freq: float) -> float:
        """Attempt to set the desired SPI clock speed

        Args:
            freq (int): desired SPI frequency

        Raises:
            DebuggerException: if an unexpected debugger response is received
            SerialException: if some communication error occurs

        Returns:
            int: actual programmed speed closest to the desired speed
        """

        # calculate fdiv and actual SPI frequency
        fdiv = ECGCDebugger.__calculate_fdiv(freq)
        actual_fspi = ECGCDebugger.__calculate_fspi(fdiv)

        # program frequency
        self.disable_auto_increment()
        self.set_address(ECGCDebugger.__CART_REG_SPI_FDIV)
        self.write(fdiv)

        logging.info(f'spi: set frequency to {actual_fspi}')

        return actual_fspi
    
    def spi_select(self, target: SpiChipSelect):
        """Select a given device on the SPI bus

        Args:
            target (SpiChipSelect): SPI device to select

        Raises:
            DebuggerException: if an unexpected debugger response is received
            SerialException: if some communication error occurs
        """

        self.disable_auto_increment()
        self.set_address(ECGCDebugger.__CART_REG_SPI_CS)
        self.write(target.value)

        logging.info(f'spi: selected {target.name}')

    def spi_deselect(self):
        """Deselect any previously selected SPI devices
        
        Raises:
            DebuggerException: if an unexpected debugger response is received
            SerialException: if some communication error occurs
        """

        self.disable_auto_increment()
        self.set_address(ECGCDebugger.__CART_REG_SPI_CS)
        self.write(SpiChipSelect.NONE.value)

        logging.info(f'spi: deselected all')

    def spi_write_read(self, write_data: bytes) -> bytes:
        """Write given data over the SPI bus and read back received data

        Note:
            One should select a specific SPI device using the `spi_select`
            method and release the device using `spi_deselect`.

        Args:
            write_data (bytes): data to write over the SPI bus

        Raises:
            DebuggerException: if an unexpected debugger response is received
            SerialException: if some communication error occurs

        Returns:
            bytes: data read back after each byte sent
        """

        # initialise write
        read_data = []
        self.disable_auto_increment()
        self.set_address(ECGCDebugger.__CART_REG_SPI_DATA)

        # perform write and read back
        for i in range(len(write_data)):
            self.write(write_data[i:i+1])
            read_data.append(self.read(1)[0])

        logging.info('spi: wrote {}'.format(' '.join([f'${b:02X}' for b in write_data])))
        logging.info('spi: read  {}'.format(' '.join([f'${b:02X}' for b in read_data])))

        return read_data
    
    def spi_write(self, write_data: bytes):
        """Write given data over the SPI bus

        Note:
            One should select a specific SPI device using the `spi_select`
            method and release the device using `spi_deselect`.

        Args:
            write_data (bytes): data to write over the SPI bus

        Raises:
            DebuggerException: if an unexpected debugger response is received
            SerialException: if some communication error occurs
        """

        self.disable_auto_increment()
        self.set_address(ECGCDebugger.__CART_REG_SPI_DATA)
        self.write(write_data)

        logging.info('spi: wrote {}'.format(' '.join([f'${b:02X}' for b in write_data])))

    def __calculate_crc7(data: bytes | bytearray) -> int:
        crc = 0

        for b in data:
            crc ^= b

            for _ in range(8):
                crc = (crc << 1) ^ (ECGCDebugger.__SPI_CRC7_POLYNOM << 1) if crc & 0x80 else crc << 1

        return crc >> 1

    def __try_read_sd_response_r1(self) -> bytearray:
        # attempt to read R1
        response = bytearray()
        for _ in range(8):
            response.extend(self.spi_write_read(b'\xFF'))

            # valid response if MSB is zero
            if not response[-1] & 0x80:
                break

        return response

    def __sd_send_cmd(self, cmd: int, arg: int, keep_selected: bool, expected_response: SDResponseType) -> SDResponse:
        # build command frame
        cmd_frame = bytearray()
        cmd_frame.extend((cmd | 0b01000000).to_bytes(1, 'big'))
        cmd_frame.extend(arg.to_bytes(4, 'big'))
        cmd_crc = ECGCDebugger.__calculate_crc7(cmd_frame)
        cmd_frame.extend(((cmd_crc << 1) | 1).to_bytes(1, 'big'))

        try:
            # write command
            self.spi_select(SpiChipSelect.SD)
            self.spi_write(cmd_frame)

            # R1 is always expected, therefore at least read that
            response_raw = self.__try_read_sd_response_r1()
            try:
                response = SDResponse(response_raw[-1])
            except ValueError:
                raise SDException(cmd, arg, response_raw, None)
            
            # raise error if R1 indicates an error
            if response.error_occurred():
                raise SDException(cmd, arg, response_raw, response)

            # extend response data based on expected response
            match expected_response:
                case SDResponseType.R1:
                    pass
                case SDResponseType.R1B:
                    response_raw.extend(self.spi_write_read(b'\xFF'))
                    response = SDResponseR1B(response, response_raw[-1:])
                case SDResponseType.R2:
                    response_raw.extend(self.spi_write_read(b'\xFF'))
                    response = SDResponseR2(response, response_raw[-1:])
                case SDResponseType.R3:
                    response_raw.extend(self.spi_write_read(b'\xFF\xFF\xFF\xFF'))
                    response = SDResponseR3(response, response_raw[-4:])
                case SDResponseType.R7:
                    response_raw.extend(self.spi_write_read(b'\xFF\xFF\xFF\xFF'))
                    response = SDResponseR7(response, response_raw[-4:])
        
            # raise error if response indicates an error
            if response.error_occurred():
                raise SDException(cmd, arg, response_raw, response)
        except Exception as e:
            # always deselect target if an exception occurs
            keep_selected = False
            raise e
        finally:
            # flush any remaining stuff
            self.spi_write(b'\xFF\xFF')

            if not keep_selected:
                self.spi_deselect()

        return response

    def sd_send_cmd(self, cmd: int, arg: int, keep_selected: bool = False) -> SDResponse:
        """Send given SD card command and return response information

        Args:
            cmd (int): cmd index
            arg (int): cmd argument
            keep_selected (bool, optional): keep the CS line selected after exiting method. Defaults to False.

        Raises:
            ValueError: if cmd is not a 6-bit unsigned integer
            ValueError: if arg is not a 32-bit unsigned integer
            SDException: if an error occurs during reading of response
            DebuggerException: if an unexpected debugger response is received
            SerialException: if some communication error occurs

        Returns:
            SDResponse: response object containing response data
        """
        
        if cmd < 0 or cmd > 0x3F:
            raise ValueError('cmd must be a 6-bit unsigned integer')
        
        if arg < 0 or arg > 0xFFFFFFFF:
            raise ValueError('arg must be a 32-bit unsigned integer')

        # send command and return response object
        expected_response = sd_cmd_get_expected_response(cmd)
        return self.__sd_send_cmd(cmd, arg, keep_selected, expected_response)

    def sd_send_acmd(self, acmd: int, arg: int, keep_selected: bool = False) -> SDResponse:
        """Send given SD card application command and return response information

        Args:
            acmd (int): acmd index
            arg (int): acmd argument
            keep_selected (bool, optional): keep the CS line selected after exiting method. Defaults to False.

        Raises:
            ValueError: if acmd is not a 6-bit unsigned integer
            ValueError: if arg is not a 32-bit unsigned integer
            SDException: if an error occurs during reading of response
            DebuggerException: if an unexpected debugger response is received
            SerialException: if some communication error occurs

        Returns:
            SDResponse: response object containing response data of tha application command
        """

        if acmd < 0 or acmd > 0x3F:
            raise ValueError('acmd must be a 6-bit unsigned integer')
        
        if arg < 0 or arg > 0xFFFFFFFF:
            raise ValueError('arg must be a 32-bit unsigned integer')

        # send CMD55 to specify that an application command is being sent
        expected_response = sd_cmd_get_expected_response(55)
        response = self.__sd_send_cmd(55, 0, False, expected_response)
        if response.error_occurred():
            raise SDException(55, arg, None, response)

        # send the actual application command
        expected_response = sd_acmd_get_expected_response(acmd)
        return self.__sd_send_cmd(acmd, arg, keep_selected, expected_response)
    