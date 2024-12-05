from pathlib import Path

from langchain_core.runnables.config import RunnableConfig
from langchain_core.messages import ToolMessage, HumanMessage
from langchain_experimental.utilities import PythonREPL

from aoc_coding_companion.utils.state import AOCState
from aoc_coding_companion.utils.models import Python_REPL
from aoc_coding_companion.utils.prompts import developer_prompt
from aoc_coding_companion.utils.utils import (
    get_model_by_config,
    get_logger_by_config,
    get_parser_by_config,
    get_leaderboard_id_by_config,
    send_telegram_message_by_config
)


def check_leader_board(_, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла проверки лидерборда')
    parser = get_parser_by_config(config)
    leaderboard_id = get_leaderboard_id_by_config(config)
    try:
        leaderboard_result = parser.parse_leaderboard(leaderboard_id)
        logger.debug(f'Результат проверки лидерборда: {leaderboard_result}')
        comment = (
            f'<ПРОВЕРКА ЛИДЕРБОРДА>: '
            f'Твое место - {leaderboard_result.my_position} с очками - {leaderboard_result.my_score}'
        )
    except Exception as e:
        comment = f'Не удалось получить результат проверки лидерборда: {e}'
    send_telegram_message_by_config(comment, config)

    return {'comment': comment}


check_leader_board.__name__ = 'Проверка списка лидеров 📊'


def search_unsolved_puzzles(_, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла поиска нерешенных задач')
    parser = get_parser_by_config(config)
    calendar = parser.parse_calendar()
    logger.debug(calendar)
    comment = (
        f'Количество нерешенных задач: {len(calendar.released.unsolved)} '
        f'и частично не решенных задач {len(calendar.released.partially_solved)}'
    )
    send_telegram_message_by_config(comment, config)
    todo_puzzle_links = list(calendar.released.unsolved.values()) + list(calendar.released.partially_solved.values())
    return {'todo_puzzle_links': todo_puzzle_links, 'comment': comment}


search_unsolved_puzzles.__name__ = 'Поиск нерешенных задач 🔎'


def get_puzzle(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла распознавания задачи и условий')
    parser = get_parser_by_config(config)
    todo_puzzle_links = state['todo_puzzle_links']
    todo_puzzle_link = todo_puzzle_links.pop()
    current_puzzle_details = parser.parse_puzzle_details(todo_puzzle_link)
    comment = (
        f'В работу взята: {current_puzzle_details}'
    )
    send_telegram_message_by_config(comment, config)
    return {'todo_puzzle_links': todo_puzzle_links, 'current_puzzle_details': current_puzzle_details, 'comment': comment}


get_puzzle.__name__ = 'Взятие задачи 👀'


def download_input(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход скачивания файла с входными данными')
    parser = get_parser_by_config(config)
    working_dir = Path(config['configurable'].get('working_dir', './tmp_work_dir')).resolve()
    working_dir.mkdir(parents=True, exist_ok=True)
    current_puzzle_details = state['current_puzzle_details']
    input_filepath = working_dir / f'INPUT({current_puzzle_details.name}).txt'
    parser.download_input(current_puzzle_details.input_link, input_filepath)
    comment = (
        f'Скачены входные данные в файл {input_filepath}'
    )
    send_telegram_message_by_config(comment, config)
    return {'input_filepath': input_filepath, 'comment': comment}


get_puzzle.__name__ = 'Взятие задачи 👀'


GET_PUZZLE_ROUTE_NAME = 'Задачи для решения еще есть'
ALL_DONE_ROUTE_NAME = 'Все задачи из TODO листа выполнены'


def route_have_puzzles(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход выбора следующего узла по парсингу задачи')
    todo_puzzle_links = state.get("todo_puzzle_links", [])
    if len(todo_puzzle_links) > 0:
        return GET_PUZZLE_ROUTE_NAME
    return ALL_DONE_ROUTE_NAME


def write_code(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла программиста')
    llm = get_model_by_config(config)

    tool_choice = None
    if len(state["messages"]) == 0:
        tool_choice = Python_REPL.__name__
    chain = developer_prompt | llm.bind_tools([Python_REPL], tool_choice=tool_choice)

    result = chain.invoke(
        {
            'input_filepath': state['input_filepath'],
            'task_description': state['current_puzzle_details'].description,
            'question': state['current_puzzle_details'].question,
            'messages': state['messages']
        }
    )
    state['messages'].append(result)

    if len(result.tool_calls) > 0:
        comment = f'Написан код:\n{result.tool_calls[0]['args']['query']}'
    else:
        comment = f'Дан финальный ответ на задачу: {result.content}'
    return {'messages': state['messages'], 'comment': comment}


write_code.__name__ = 'Программист 👨🏻‍💻'


def exec_code(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла запуска кода')
    tool_calls = state["messages"][-1].tool_calls
    if len(tool_calls) != 1:
        raise ValueError(f'Вызовов инструмента более 1.\n{tool_calls}')
    tool_call = tool_calls[0]
    if tool_call['name'] != Python_REPL.__name__:
        raise ValueError(f'Вызывают не инструмент по исполнению кода {Python_REPL.__name__}.\n{tool_call}')
    code_output = PythonREPL().run(command=tool_call['args']['query'])
    state['messages'].append(ToolMessage(content=code_output, tool_call_id=tool_call['id']))
    comment = f'Результат выполнения кода: {code_output}'
    send_telegram_message_by_config(comment, config)
    return {"messages": state['messages'], 'comment': comment}


exec_code.__name__ = 'Запуск кода 🚀'


EXEC_CODE_ROUTE_NAME = 'Требуется запуск кода'
FIND_ANSWER_ROUTE_NAME = 'Получен финальный ответ'


def route_exec_code(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход выбора следующего узла по запуску кода')
    messages = state.get("messages", [])
    if len(messages) > 0:
        last_message = messages[-1]
    else:
        raise ValueError(f"Нет сообщений в состоянии графа: {state}")
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return EXEC_CODE_ROUTE_NAME
    return FIND_ANSWER_ROUTE_NAME


def answer_submit(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла отправки ответа')
    parser = get_parser_by_config(config)

    answer = state['messages'][-1].content
    result = parser.submit_answer(state['current_puzzle_details'].submit_url, state['current_puzzle_details'].level, answer)

    if result.is_correct:
        comment = f'Ответ "{result}" верный! '
    else:
        comment = f'Ответ "{result}" неверный!'
        state['messages'].append(
            HumanMessage('Ответ неверный. Где-то есть ошибка, еще раз прочитай условие и перепиши код')
        )
    send_telegram_message_by_config(comment, config)
    return {'messages': state['messages'], 'comment': comment}


answer_submit.__name__ = 'Отправка ответа 💌'


RETRY_ROUTE_NAME = 'Ответ неверный, пробуем еще'
ANSWER_CORRECTNESS_ROUTE_NAME = 'Ответ верный!'


def route_answer_correctness(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход выбора следующего узла по правильности ответа')

    if isinstance(HumanMessage, state['messages'][-1]):
        return RETRY_ROUTE_NAME
    return ' | '.join([ANSWER_CORRECTNESS_ROUTE_NAME, route_have_puzzles(state, config)])