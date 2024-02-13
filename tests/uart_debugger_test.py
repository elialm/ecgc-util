import unittest

from src.uart_debugger import UartDebugger, DebuggerException

class TestUartDebugger(unittest.TestCase):
    # Change to whatever COM port the test should use
    COM_PORT = 'COM3'

    def test_debugger_creation(self):
        debugger = UartDebugger(self.COM_PORT)

        self.assertFalse(debugger.is_enabled())
    
    def test_debugger_enable(self):
        debugger = UartDebugger(self.COM_PORT)

        debugger.enable_core()
        self.assertTrue(debugger.is_enabled())

    def test_debugger_disable(self):
        debugger = UartDebugger(self.COM_PORT)

        debugger.enable_core()
        debugger.disable_core()
        self.assertFalse(debugger.is_enabled())

    def test_debugger_improper_double_enable(self):
        debugger = UartDebugger(self.COM_PORT)
        debugger.enable_core()

        with self.assertRaises(DebuggerException):
            debugger.enable_core()

    def test_debugger_improper_disable(self):
        debugger = UartDebugger(self.COM_PORT)

        with self.assertRaises(DebuggerException):
            debugger.disable_core()

    def test_set_address(self):
        debugger = UartDebugger(self.COM_PORT)

        with debugger:
            debugger.set_address(0x0100)

    def test_set_address_core_disabled(self):
        debugger = UartDebugger(self.COM_PORT)

        with self.assertRaises(DebuggerException):
            debugger.set_address(0x0100)

    def test_set_address_negative(self):
        debugger = UartDebugger(self.COM_PORT)

        with self.assertRaises(ValueError):
            with debugger:
                debugger.set_address(-1)

    def test_set_address_too_large(self):
        debugger = UartDebugger(self.COM_PORT)

        with self.assertRaises(ValueError):
            with debugger:
                debugger.set_address(0x10000)

    def test_enable_auto_increment(self):
        debugger = UartDebugger(self.COM_PORT)

        with debugger:
            debugger.enable_auto_increment()

    def test_enable_auto_increment_core_disabled(self):
        debugger = UartDebugger(self.COM_PORT)

        with self.assertRaises(DebuggerException):
            debugger.enable_auto_increment()

    def test_disable_auto_increment(self):
        debugger = UartDebugger(self.COM_PORT)

        with debugger:
            debugger.disable_auto_increment()

    def test_disable_auto_increment_core_disabled(self):
        debugger = UartDebugger(self.COM_PORT)

        with self.assertRaises(DebuggerException):
            debugger.disable_auto_increment()

    def test_write_read_amount_divisible_in_even_bursts(self):
        debugger = UartDebugger(self.COM_PORT)
        write_data = b'\xc3[B>\xfa\xaf\xcb&\x1a\xaa\x98@\x03\xf5\x9a\x05'
        read_data = b''

        with debugger:
            debugger.set_address(0x4000)
            debugger.enable_auto_increment()
            debugger.write(write_data)
            debugger.set_address(0x4000)
            read_data = debugger.read(16)

        self.assertEqual(write_data, read_data)

    def test_write_read_amount_not_divisible_in_even_bursts(self):
        debugger = UartDebugger(self.COM_PORT)
        write_data = b'\x0f)\xa3S1\xcdc\x07\xbf\xa1\xcf\xef\xf4\x0b}'
        read_data = b''

        with debugger:
            debugger.set_address(0x4000)
            debugger.enable_auto_increment()
            debugger.write(write_data)
            debugger.set_address(0x4000)
            read_data = debugger.read(15)

        self.assertEqual(write_data, read_data)

    def test_read_from_address_zero(self):
        debugger = UartDebugger(self.COM_PORT)

        with debugger:
            debugger.set_address(0)
            debugger.enable_auto_increment()
            debugger.read(1024)
