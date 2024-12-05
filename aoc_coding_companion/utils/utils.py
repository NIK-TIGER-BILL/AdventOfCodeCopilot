import os
from logging import Logger
from functools import lru_cache

from telegram import Bot
from langchain_openai import ChatOpenAI
from langchain_core.runnables.config import RunnableConfig
from langchain_gigachat.chat_models.gigachat import GigaChat
from langchain_core.language_models.chat_models import BaseChatModel

from aoc_coding_companion.utils.logger import get_logger
from aoc_coding_companion.utils.parser import ParserConfig, AdventOfCodeParser


@lru_cache(maxsize=4)
def get_model_by_name(model_name: str) -> BaseChatModel:
    if model_name == 'openai-omni':
        model = ChatOpenAI(
            temperature=1,
            request_timeout=90.0,
            model=os.getenv('OPENAI_MODEL', 'gpt-4o')
        )
    elif model_name == 'giga-pro':
        model = GigaChat(
            model='GigaChat-Pro',
            temperature=1,
            top_p=1,
            timeout=90.0,
            verify_ssl_certs=False,
            profanity_check=False,
        )
    elif model_name == 'giga-max':
        model = GigaChat(
            model='GigaChat-Max',
            temperature=1,
            top_p=1,
            timeout=90.0,
            verify_ssl_certs=False,
            profanity_check=False,
        )
    else:
        raise ValueError(f'Модель с именем "{model_name}" не поддерживается')
    return model


def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    bot = Bot(token=token)
    bot.send_message(chat_id=chat_id, text=message)


def send_telegram_message_by_config(message: str, config: RunnableConfig) -> None:
    try:
        chat_id = config['configurable'].get('chat_id', os.getenv('TELEGRAM_CHAT_ID'))
        if chat_id is None:
            return
        token = os.environ['TELEGRAM_BOT_TOKEN']
        send_telegram_message(token, chat_id, message)
    except Exception as e:
        logger = get_logger_by_config(config)
        logger.error(f'Ошибка отправки сообщения в телеграм: {e}')


@lru_cache(maxsize=4)
def get_model_by_config(config: RunnableConfig) -> BaseChatModel:
    return get_model_by_name(config['configurable'].get('model', 'openai-omni'))

@lru_cache(maxsize=4)
def get_leaderboard_id_by_config(config: RunnableConfig) -> BaseChatModel:
    return get_model_by_name(config['configurable'].get('leaderboard_id', os.environ['AOC_LEADERBOARD_ID']))


@lru_cache(maxsize=4)
def get_logger_by_config(config: RunnableConfig) -> Logger:
    logger = config['configurable'].get('logger')
    if logger is None:
        logger = get_logger()
    return logger


@lru_cache(maxsize=4)
def get_parser_by_config(config: RunnableConfig) -> AdventOfCodeParser:
    session_token = config['configurable']['session_token']
    config = ParserConfig(
        headers={
            'User-Agent': os.environ.get('AOC_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0) Gecko/20100101 Firefox/92.0'),
        },
        cookies={
            'session': session_token,
        }
    )
    return AdventOfCodeParser(config)
