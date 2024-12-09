from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage

from aoc_coding_companion.utils.parser import PuzzleDetail


class AOCState(TypedDict):
    messages: list[AnyMessage]
    todo_puzzle_links: list[str]
    current_puzzle_details: PuzzleDetail
    input_filepath: str
    comment: str
    attempt_number: int
