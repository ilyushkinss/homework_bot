class EndpointException(Exception):
    """Исключение для ответа API."""


class ResponseException(Exception):
    """Исключение для данных API."""


class ParseException(Exception):
    """Исключение для извлекаемых данных API."""


class MessageError(Exception):
    """Исключение отправки сообщений."""


class WrongStatusCode(Exception):
    """Не правильный статус код."""
