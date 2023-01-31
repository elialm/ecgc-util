import unittest

from ecgc_util.spi_debug import SpiDebugger, DebuggerException

class TestSpiDebugger(unittest.TestCase):
    # Change to whatever COM port the test should use
    COM_PORT = 'COM4'

    def test_debugger_creation(self):
        debugger = SpiDebugger(self.COM_PORT)

        self.assertFalse(debugger.is_enabled())
    
    def test_debugger_enable(self):
        debugger = SpiDebugger(self.COM_PORT)

        debugger.enable_core()
        self.assertTrue(debugger.is_enabled())

    def test_debugger_disable(self):
        debugger = SpiDebugger(self.COM_PORT)

        debugger.enable_core()
        debugger.disable_core()
        self.assertFalse(debugger.is_enabled())

    def test_debugger_improper_double_enable(self):
        debugger = SpiDebugger(self.COM_PORT)
        debugger.enable_core()

        with self.assertRaises(DebuggerException):
            debugger.enable_core()

    def test_debugger_improper_disable(self):
        debugger = SpiDebugger(self.COM_PORT)

        with self.assertRaises(DebuggerException):
            debugger.disable_core()

    def test_set_address(self):
        debugger = SpiDebugger(self.COM_PORT)

        with debugger:
            debugger.set_address(0x0100)

    def test_set_address_core_disabled(self):
        debugger = SpiDebugger(self.COM_PORT)

        with self.assertRaises(DebuggerException):
            debugger.set_address(0x0100)

    def test_set_address_negative(self):
        debugger = SpiDebugger(self.COM_PORT)

        with self.assertRaises(ValueError):
            with debugger:
                debugger.set_address(-1)

    def test_set_address_too_large(self):
        debugger = SpiDebugger(self.COM_PORT)

        with self.assertRaises(ValueError):
            with debugger:
                debugger.set_address(0x10000)

    def test_enable_auto_increment(self):
        debugger = SpiDebugger(self.COM_PORT)

        with debugger:
            debugger.enable_auto_increment()

    def test_enable_auto_increment_core_disabled(self):
        debugger = SpiDebugger(self.COM_PORT)

        with self.assertRaises(DebuggerException):
            debugger.enable_auto_increment()

    def test_disable_auto_increment(self):
        debugger = SpiDebugger(self.COM_PORT)

        with debugger:
            debugger.disable_auto_increment()

    def test_disable_auto_increment_core_disabled(self):
        debugger = SpiDebugger(self.COM_PORT)

        with self.assertRaises(DebuggerException):
            debugger.disable_auto_increment()

    
