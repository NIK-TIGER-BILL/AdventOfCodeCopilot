import logging
from functools import lru_cache
from logging.handlers import RotatingFileHandler

from aoc_coding_companion.utils.constants import LOGGER_NAME, LOGGER_LEVEL, LOGGER_FILEPATH, LOGGER_DIRPATH


@lru_cache()
def get_logger():
    # Создаем директорию для логов
    LOGGER_DIRPATH.mkdir(parents=True, exist_ok=True)

    # Настройка логгера
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(LOGGER_LEVEL)

    # Создаем обработчик для вывода логов в файл с ротацией
    file_handler = RotatingFileHandler(LOGGER_FILEPATH, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)

    # Создаем обработчик для вывода логов в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOGGER_LEVEL)

    # Формат для логов
    formatter = logging.Formatter('[%(name)s][%(filename)s->%(funcName)s():%(lineno)3s]'
                                  '[%(asctime)s][%(levelname)s]: %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Добавляем обработчики к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
