from .spi_debugger import SerialException, DebuggerException
import logging

def log_info(ex: DebuggerException | SerialException) -> None:
    if isinstance(ex, DebuggerException):
        if ex.is_unexpected_response_error():
            if ex.actual_response == 'EFLUSH':
                logging.info('this error typically indicates an electrical error. Check the debugger wiring.')
