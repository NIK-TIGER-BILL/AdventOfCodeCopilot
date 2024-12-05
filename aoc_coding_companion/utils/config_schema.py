from typing import Literal, Optional, TypedDict


class ConfigSchema(TypedDict):
    """Схема конфигурации"""

    model: Optional[Literal['openai-omni', 'giga-pro', 'giga-max']]
    session_token: str
    telegram_id: int
    leaderboard_id: int
    working_dir: str
