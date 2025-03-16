class EndpointException(Exception):
    """Исключение для ответа API."""

    pass


class ResponseException(Exception):
    """Исключение для данных API."""

    pass


class ParseException(Exception):
    """Исключение для извлекаемых данных API."""

    pass


class MessageError(Exception):
    """Исключение отправки сообщений."""

    pass


class WrongStatusCode(Exception):
    """Не правильный статус код."""

    pass
