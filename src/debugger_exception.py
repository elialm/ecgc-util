class DebuggerException(Exception):
    """Exception thrown when an error occurs during Debugger operations"""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args)

        self.expected_response = kwargs.get('expected_response', None)
        self.actual_response = kwargs.get('actual_response', None)
        self.action_description = kwargs.get('action_description', None)
        self.__is_unexpected_response_error = self.expected_response and self.expected_response and self.action_description

    def __str__(self) -> str:
        if self.__is_unexpected_response_error:
            return 'unexpected debugger response during {}: expected \"{}\", got \"{}\"'.format(
                self.action_description, self.expected_response, self.actual_response)
        else:
            return super().__str__()

    def is_unexpected_response_error(self) -> bool:
        return self.__is_unexpected_response_error