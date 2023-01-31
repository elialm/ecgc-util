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

    
