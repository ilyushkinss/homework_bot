import logging
import os
import requests
from http import HTTPStatus
import time

from dotenv import load_dotenv
from telebot import TeleBot

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


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='logs.log',
    encoding='utf-8',
)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical('Некорректные переменные окружения')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщений."""
    logging.debug(f'Отправлено сообщение: "{message}"')
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API сервиса Практикум.Домашка."""
    current_timestamp = timestamp or int(time.time())
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        logging.error(f'Эндпоинт {ENDPOINT} недоступен: {error}')
        raise exceptions.EndpointException

    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error(f'Код ответа: {homework_statuses.status_code}')
        raise exceptions.EndpointException

    try:
        return homework_statuses.json()
    except Exception as error:
        logging.error(f'Невозможно преобразовать к формату json: {error}')
        raise exceptions.EndpointException


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if type(response) is not dict:
        logging.error('Тип данных в ответе API не соответствует ожидаемому')
        raise TypeError

    if 'homeworks' not in response:
        logging.error('Ключ "homeworks" отсутствует')
        raise exceptions.ResponseException('Ключ "homeworks" отсутствует')

    homeworks_list = response['homeworks']
    if type(homeworks_list) != list:
        logging.error(
            'Тип данных "homeworks_list" не соответствует ожидаемому'
        )
        raise TypeError

    return homeworks_list


def parse_status(homework):
    """Извлекает статус конкретной домашки."""
    if 'homework_name' not in homework:
        logging.error('Ключ "homework_name" недоступен')
        raise KeyError('Ключ "homework_name" недоступен')

    if 'status' not in homework:
        logging.error('Ключ "status" недоступен')
        raise KeyError('Ключ "status" недоступен')

    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error(f'Неизвестный статус работы {homework_name}')
        raise exceptions.ParseeException


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError('Некорректные переменные окружения')

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_status = ''
    current_error = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if len(homework) == 0:
                logging.debug('Статус не обновлен')
            else:
                homework_status = parse_status(homework[0])
                if current_status == homework_status:
                    logging.info(homework_status)
                else:
                    current_status = homework_status
                    send_message(bot, homework_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if current_error != str(error):
                current_error = str(error)
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
