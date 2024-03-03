from __future__ import annotations
from .uart_debugger import UartDebugger, DebuggerException, SerialException
from enum import Enum


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

    __SPI_DEFAULT_CTRL = (0b00000001).to_bytes(1, 'little')
    __SPI_DEFAULT_FDIV = (49).to_bytes(1, 'little')
    __SPI_DEFAULT_CS = (0xFF).to_bytes(1, 'little')
    __SPI_FCLK = 100_000_000

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
        self.set_address(ECGCDebugger.__CART_REG_SPI_FDIV)
        self.write(ECGCDebugger.__SPI_DEFAULT_FDIV)
        self.set_address(ECGCDebugger.__CART_REG_SPI_CS)
        self.write(ECGCDebugger.__SPI_DEFAULT_CS)

    def __calculate_fspi(fdiv: int) -> int:
        if fdiv < 0 or fdiv > 0xFF:
            raise ValueError('fdiv must be an 8-bit unsigned integer')
        
        return ECGCDebugger.__SPI_FCLK / (fdiv + 1)
    
    def __calculate_fdiv(fspi: int) -> int:
        return (ECGCDebugger.__SPI_FCLK / fspi) - 1

    def spi_set_speed(self, freq: int) -> int:
        """Attempt to set the desired SPI clock speed

        Args:
            freq (int): desired SPI frequency

        Returns:
            int: actual programmed speed closest to the desired speed
        """

        raise NotImplementedError()
    
    def spi_select(self, target: SpiChipSelect):
        """Select a given device on the SPI bus

        Args:
            target (SpiChipSelect): SPI device to select
        """

        self.disable_auto_increment()
        self.set_address(ECGCDebugger.__CART_REG_SPI_CS)
        self.write(target.value)

    def spi_deselect(self):
        """Deselect any previously selected SPI devices"""

        self.disable_auto_increment()
        self.set_address(ECGCDebugger.__CART_REG_SPI_CS)
        self.write(SpiChipSelect.NONE.value)

    def spi_write(self, write_data: bytes) -> bytes:
        """Write given data over the SPI bus

        Note:
            One should select a specific SPI device using the `spi_select`
            method and release the device using `spi_deselect`.

        Args:
            write_data (bytes): data to write over the SPI bus

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

        return read_data