from pathlib import Path
from datetime import datetime

from langchain_core.messages import ToolMessage
from langchain_core.runnables.config import RunnableConfig

from aoc_coding_companion.utils.state import AOCState
from aoc_coding_companion.utils.tools import run_python_code
from aoc_coding_companion.utils.prompts import developer_prompt
from aoc_coding_companion.utils.models import PythonREPL, TaskAnswer
from aoc_coding_companion.utils.utils import (
    get_model_by_config,
    get_logger_by_config,
    get_parser_by_config,
    get_leaderboard_id_by_config,
    send_telegram_message_by_config
)


async def start_alert(_, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла оповещение о старте работы')
    comment = f'Оооо привет! Ержан 🙈 проснулся и начал работу.\nВремя {datetime.now()}'
    send_telegram_message_by_config(comment, config)

    return {'comment': comment}

start_alert.__name__ = 'Оповещение о старте работы 🚀'


async def check_leader_board(_, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла проверки лидерборда')
    leaderboard_id = get_leaderboard_id_by_config(config)
    try:
        async with get_parser_by_config(config) as parser:
            leaderboard_result = await parser.parse_leaderboard(leaderboard_id)
        logger.debug(f'Результат проверки лидерборда: {leaderboard_result}')
        comment = (
            f'<ПРОВЕРКА ЛИДЕРБОРДА>: '
            f'Твое место - {leaderboard_result.my_position} с очками - {leaderboard_result.my_points}'
        )
    except Exception as e:
        comment = f'Не удалось получить результат проверки лидерборда: {e}'
    send_telegram_message_by_config(comment, config)

    return {'comment': comment}

check_leader_board.__name__ = 'Проверка списка лидеров 📊'


async def search_unsolved_puzzles(_, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла поиска нерешенных задач')
    async with get_parser_by_config(config) as parser:
        calendar = await parser.parse_calendar()
    logger.debug(calendar)
    comment = (
        f'Количество нерешенных задач: {len(calendar.released.unsolved)} '
        f'и частично не решенных задач {len(calendar.released.partially_solved)}'
    )
    send_telegram_message_by_config(comment, config)
    todo_puzzle_links = list(calendar.released.partially_solved.values()) + list(calendar.released.unsolved.values())
    return {'todo_puzzle_links': todo_puzzle_links, 'comment': comment}

search_unsolved_puzzles.__name__ = 'Поиск нерешенных задач 🔎'


async def get_puzzle(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла распознавания задачи и условий')
    todo_puzzle_links = state['todo_puzzle_links']
    todo_puzzle_link = todo_puzzle_links.pop(0)
    async with get_parser_by_config(config) as parser:
        current_puzzle_details = await parser.parse_puzzle_details(todo_puzzle_link)
    comment = (
        f'Взято в работу:\n{current_puzzle_details}'
    )
    send_telegram_message_by_config(comment, config)
    return {
        'todo_puzzle_links': todo_puzzle_links,
        'current_puzzle_details': current_puzzle_details,
        'comment': comment,
        'messages': []
    }

get_puzzle.__name__ = 'Взятие задачи 👀'


async def download_input(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход скачивания файла с входными данными')
    working_dir = Path(config['configurable'].get('working_dir', './tmp_work_dir')).resolve()
    working_dir.mkdir(parents=True, exist_ok=True)
    current_puzzle_details = state['current_puzzle_details']
    input_filepath = working_dir / f'INPUT({current_puzzle_details.name}).txt'
    async with get_parser_by_config(config) as parser:
        await parser.download_input(current_puzzle_details.input_link, input_filepath)
    comment = (
        f'Скачены входные данные в файл {input_filepath}'
    )
    send_telegram_message_by_config(comment, config)
    return {'input_filepath': input_filepath, 'comment': comment}

download_input.__name__ = 'Скачивание входных данных ⏳'


GET_PUZZLE_ROUTE_NAME = 'Задачи для решения еще есть'
ALL_DONE_ROUTE_NAME = 'Все задачи из TODO листа выполнены'


async def route_have_puzzles(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход выбора следующего узла по парсингу задачи')
    todo_puzzle_links = state.get("todo_puzzle_links", [])
    if len(todo_puzzle_links) > 0:
        return GET_PUZZLE_ROUTE_NAME
    return ALL_DONE_ROUTE_NAME


async def write_code(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла программиста')
    llm = get_model_by_config(config)

    messages = state.get('messages', [])
    if len(messages) == 0:
        tool_choice = PythonREPL.__name__
    else:
        tool_choice = True
    chain = developer_prompt | llm.bind_tools([PythonREPL, TaskAnswer], tool_choice=tool_choice)

    result = await chain.ainvoke(
        {
            'input_filepath': state['input_filepath'],
            'task_description': state['current_puzzle_details'].description,
            'question': state['current_puzzle_details'].question,
            'messages': messages
        }
    )
    messages.append(result)

    if result.tool_calls[0]['name'] == PythonREPL.__name__:
        code = result.tool_calls[0]['args']['query']
        comment = f'Написан код:\n```python\n{code}\n```'
    else:
        answer = result.tool_calls[0]['args']['answer']
        comment = f'Дан финальный ответ на задачу: {answer}'
    return {'messages': messages, 'comment': comment}


write_code.__name__ = 'Программист 👨🏻‍💻'


async def exec_code(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла запуска кода')
    tool_calls = state["messages"][-1].tool_calls
    if len(tool_calls) != 1:
        raise ValueError(f'Вызовов инструмента более 1.\n{tool_calls}')
    tool_call = tool_calls[0]
    if tool_call['name'] != PythonREPL.__name__:
        raise ValueError(f'Вызывают не инструмент по исполнению кода {PythonREPL.__name__}.\n{tool_call}')
    code_output = run_python_code(code=tool_call['args']['query']).strip(' \n')
    state['messages'].append(ToolMessage(content=code_output, tool_call_id=tool_call['id']))
    comment = f'Результат выполнения кода: "{code_output}"'
    send_telegram_message_by_config(comment, config)
    return {"messages": state['messages'], 'comment': comment}


exec_code.__name__ = 'Запуск кода 🚀'


EXEC_CODE_ROUTE_NAME = 'Требуется запуск кода'
FIND_ANSWER_ROUTE_NAME = 'Получен финальный ответ'


async def route_exec_code(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход выбора следующего узла по запуску кода')
    tool_calls = state["messages"][-1].tool_calls
    if len(tool_calls) == 1 and tool_calls[0]['name'] == PythonREPL.__name__:
        return EXEC_CODE_ROUTE_NAME
    return FIND_ANSWER_ROUTE_NAME


async def answer_submit(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла отправки ответа')

    all_tool_call_answer = [message.tool_calls[0] for message in state['messages']
                            if hasattr(message, 'tool_calls') and
                            len(message.tool_calls) == 1 and
                            message.tool_calls[0]['name'] == TaskAnswer.__name__]
    answers = [tool_call['args']['answer'].strip(' \n') for tool_call in all_tool_call_answer]
    submit_answer = answers.pop(-1)

    # Если такой ответ ранее был
    if submit_answer in answers:
        comment = f'Данный ответ уже ранее отвечался и был неверным'
        state['messages'].append(
            ToolMessage(
                content=f'The answer is incorrect. You have already answered "{submit_answer}" before. '
                        f'DO NOT REPEAT IT. '
                        f'Reread the terms carefully and try to find the mistake.',
                tool_call_id=all_tool_call_answer[-1]['id']
            )
        )
        return {'messages': state['messages'], 'comment': comment}

    # Отправка ответа
    async with get_parser_by_config(config) as parser:
        result = await parser.submit_answer(
            state['current_puzzle_details'].submit_url,
            state['current_puzzle_details'].level,
            submit_answer
        )

    # Если ответ верный
    if result.is_correct:
        comment = f'Ответ "{submit_answer}" верный!\n{result.full_text}'
        send_telegram_message_by_config(comment, config)
        return {'comment': comment}

    # Если ответ неверный
    comment = f'Ответ "{submit_answer}" неверный!\n{result.full_text}'
    state['messages'].append(
        ToolMessage(
            content='The answer is incorrect. '
                    'There is an error somewhere, read the condition again and rewrite the code',
            tool_call_id=all_tool_call_answer[-1]['id']
        )
    )
    send_telegram_message_by_config(comment, config)
    return {'messages': state['messages'], 'comment': comment}


answer_submit.__name__ = 'Отправка ответа 💌'


RETRY_ROUTE_NAME = 'Ответ неверный, пробуем еще'
ANSWER_CORRECTNESS_ROUTE_NAME = 'Ответ верный!'


async def route_answer_correctness(state: AOCState, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход выбора следующего узла по правильности ответа')

    if isinstance(state['messages'][-1], ToolMessage):
        return RETRY_ROUTE_NAME
    return ' | '.join([ANSWER_CORRECTNESS_ROUTE_NAME, route_have_puzzles(state, config)])


async def end_alert(_, config: RunnableConfig):
    logger = get_logger_by_config(config)
    logger.debug('Вход узла оповещение о завершении работы')
    comment = f'Я закончить, начальника!\nВремя {datetime.now()}'
    send_telegram_message_by_config(comment, config)

    return {'comment': comment}

end_alert.__name__ = 'Оповещение о конце работы 🏁'
