import os
import logging
from pathlib import Path

# Константы путей
UTILS_PATH = Path(__file__).parent.resolve()
PROJECT_PATH = UTILS_PATH.parent

LOGGER_NAME = 'aoc_coding_companion'
LOGGER_LEVEL = logging.DEBUG if 'SIMULATOR_DEBUG' in os.environ else logging.INFO
LOGGER_DIRPATH = PROJECT_PATH / 'logs'
LOGGER_FILEPATH = LOGGER_DIRPATH / f'{LOGGER_NAME}.log'

DEFAULT_ATTEMPT_COUNT = 5
DEFAULT_TIMEOUT_EXEC_CODE = 120
