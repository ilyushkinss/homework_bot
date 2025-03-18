import logging
import os
from http import HTTPStatus
import time
import sys

from dotenv import load_dotenv
import telebot
import requests

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

log_format = ('%(asctime)s - %(levelname)s'
              ' - %(message)s - %(funcName)s - %(lineno)d')

log_file = os.path.join(os.path.dirname(__file__), 'logs.log')

logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if __name__ == '__main__':
    logger.info("Логгер настроен и готов к использованию.")


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    tokens_availability = True
    for token in tokens:
        if not tokens[token]:
            tokens_availability = False
            logger.critical(
                f'Некорректные переменные окружения: {token}'
            )
    return tokens_availability


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        logging.debug(f'Отправлено сообщение: "{message}"')
        return bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise exceptions.MessageError(
            f'Боту не удалось отправить сообщение: "{error}"'
        )


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API сервиса Практикум.Домашка."""
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        raise exceptions.EndpointException(
            f'Эндпоинт {ENDPOINT} недоступен: {error}. Время: {timestamp}'
        )

    if homework_statuses.status_code != HTTPStatus.OK:
        raise exceptions.WrongStatusCode(
            f'Статус код: {homework_statuses.status_code}'
        )

    try:
        return homework_statuses.json()
    except Exception as error:
        raise exceptions.ResponseException(
            f'Невозможно преобразовать к формату json: {error}'
        )


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if not isinstance(response, dict):
        raise TypeError(
            ('Тип данных в ответе API не соответствует ожидаемому.'
             f' Ожидался тип "dict", в ответе тип "{type(response)}".')
        )

    if 'homeworks' not in response:
        raise exceptions.ResponseException(
            'Ключ "homeworks" отсутствует в коллекции "response".'
        )

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            ('Тип данных "homeworks" не соответствует ожидаемому.'
             f' Ожидался тип "dict", в ответе тип "{type(homeworks)}".')
        )

    return homeworks


def parse_status(homework):
    """Извлекает статус конкретной домашки."""
    if 'homework_name' not in homework:
        raise KeyError(
            'Ключ "homework_name" отсутствует в коллекции "homework".'
        )

    if 'status' not in homework:
        raise KeyError(
            'Ключ "status" отсутствует в коллекции "homework".'
        )

    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.ParseException(
            f'Неизвестный статус работы {homework_name}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError('Некорректные переменные окружения')

    bot = telebot.TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    current_status = ''
    last_error = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not homework:
                logging.debug('Статус не обновлен')
                continue
            homework_status = parse_status(homework[0])
            if current_status != homework_status:
                send_message(bot, homework_status)
                timestamp = int(time.time())
                current_status = homework_status
        except Exception as error:
            error_message = str(error)
            logger.error(f'Сбой в работе программы: {error_message}')
            if last_error != error_message:
                send_message(bot, f'Сбой в работе программы: {error_message}')
                last_error = error_message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
