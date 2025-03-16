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


# logging.basicConfig(
#     format=('%(asctime)s - %(levelname)s '
#             '- %(message)s - %(funcName)s - %(lineno)d'),
#     level=logging.DEBUG,
#     filename='logs.log',
#     encoding='utf-8',
#     handlers=
# )
logging.basicConfig(
    level=logging.DEBUG,
    filename='logs.log',
    format=('%(asctime)s - %(levelname)s '
            '- %(message)s - %(funcName)s - %(lineno)d'),
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    tokens_names = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    for i in range(len(tokens)):
        if not tokens[i]:
            logger.critical(
                f'Некорректные переменные окружения: {tokens_names[i]}'
            )
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


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
            f'Эндпоинт {ENDPOINT} недоступен: {error}'
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
    if isinstance(response, dict) is not True:
        raise TypeError('Тип данных в ответе API не соответствует ожидаемому')

    if 'homeworks' not in response:
        raise exceptions.ResponseException('Ключ "homeworks" отсутствует')

    homeworks_list = response['homeworks']
    if isinstance(homeworks_list, list) is not True:
        raise TypeError(
            'Тип данных "homeworks_list" не соответствует ожидаемому'
        )

    return homeworks_list


def parse_status(homework):
    """Извлекает статус конкретной домашки."""
    if 'homework_name' not in homework:
        raise KeyError('Ключ "homework_name" недоступен')

    if 'status' not in homework:
        raise KeyError('Ключ "status" недоступен')

    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise exceptions.ParseException(
            f'Неизвестный статус работы {homework_name}'
        )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError('Некорректные переменные окружения')

    bot = telebot.TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    current_status = ''
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
            logger.error(f'{str(error)}')
            send_message(bot, f'{str(error)}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
