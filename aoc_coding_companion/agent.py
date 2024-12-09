import asyncio

from psycopg_pool import AsyncConnectionPool
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from aoc_coding_companion.utils.state import AOCState
from aoc_coding_companion.utils.config_schema import ConfigSchema
from aoc_coding_companion.utils.nodes import (
    start_alert,
    end_alert,
    check_leader_board,
    search_unsolved_puzzles,
    get_puzzle,
    download_input,
    route_have_puzzles,
    write_code,
    exec_code,
    route_exec_code,
    answer_submit,
    route_answer_correctness,
    FIND_ANSWER_ROUTE_NAME,
    ALL_DONE_ROUTE_NAME,
    RETRY_ROUTE_NAME,
    EXEC_CODE_ROUTE_NAME,
    ANSWER_CORRECTNESS_ROUTE_NAME,
    GET_PUZZLE_ROUTE_NAME,
    MAX_ATTEMPT_NAME
)


def make_graph(checkpointer: BaseCheckpointSaver = None) -> CompiledStateGraph:
    """Создание компилированного графа"""

    base_builder = StateGraph(AOCState, ConfigSchema)

    base_builder.add_node(start_alert.__name__, start_alert)
    base_builder.add_node(end_alert.__name__, end_alert)
    base_builder.add_node(check_leader_board.__name__, check_leader_board)
    base_builder.add_node(search_unsolved_puzzles.__name__, search_unsolved_puzzles)
    base_builder.add_node(get_puzzle.__name__, get_puzzle)
    base_builder.add_node(download_input.__name__, download_input)
    base_builder.add_node(write_code.__name__, write_code)
    base_builder.add_node(exec_code.__name__, exec_code)
    base_builder.add_node(answer_submit.__name__, answer_submit)

    base_builder.add_edge(START, start_alert.__name__)
    base_builder.add_edge(start_alert.__name__, search_unsolved_puzzles.__name__)
    base_builder.add_conditional_edges(
        search_unsolved_puzzles.__name__,
        route_have_puzzles,
        {
            ALL_DONE_ROUTE_NAME: check_leader_board.__name__,
            GET_PUZZLE_ROUTE_NAME: get_puzzle.__name__
        }
    )
    base_builder.add_edge(check_leader_board.__name__, end_alert.__name__)
    base_builder.add_edge(end_alert.__name__, END)
    base_builder.add_edge(get_puzzle.__name__, download_input.__name__)
    base_builder.add_edge(download_input.__name__, write_code.__name__)
    base_builder.add_conditional_edges(
        write_code.__name__,
        route_exec_code,
        {
            EXEC_CODE_ROUTE_NAME: exec_code.__name__,
            FIND_ANSWER_ROUTE_NAME: answer_submit.__name__
        }
    )
    base_builder.add_edge(exec_code.__name__, write_code.__name__)
    base_builder.add_conditional_edges(
        answer_submit.__name__,
        route_answer_correctness,
        {
            RETRY_ROUTE_NAME: write_code.__name__,
            ' | '.join([ANSWER_CORRECTNESS_ROUTE_NAME, ALL_DONE_ROUTE_NAME]): search_unsolved_puzzles.__name__,
            ' | '.join([ANSWER_CORRECTNESS_ROUTE_NAME, GET_PUZZLE_ROUTE_NAME]): get_puzzle.__name__,
            ' | '.join([MAX_ATTEMPT_NAME, ALL_DONE_ROUTE_NAME]): search_unsolved_puzzles.__name__,
            ' | '.join([MAX_ATTEMPT_NAME, GET_PUZZLE_ROUTE_NAME]): get_puzzle.__name__,
        }
    )

    graph = base_builder.compile(checkpointer=checkpointer)
    return graph


async def make_graph_async_postgresql(pool: AsyncConnectionPool, setup: bool = False) -> CompiledStateGraph:
    """Создание графа с асинхронным подключением к postgresql"""
    checkpointer = AsyncPostgresSaver(pool)
    if setup:
        await checkpointer.setup()

    return make_graph(checkpointer)


async def make_graph_memory() -> CompiledStateGraph:
    """Создание графа с асинхронным подключением к postgresql"""
    checkpointer = MemorySaver()
    return make_graph(checkpointer)

if __name__ == '__main__':
    asyncio.run(make_graph_memory())
