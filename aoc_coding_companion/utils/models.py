from pydantic import BaseModel, Field


class PythonREPL(BaseModel):
    """Python-интерпретатор. Используйте его для выполнения команд на Python"""
    query: str = Field(description="Фрагмент python кода для решение задачи с выводом результата в консоль")


class TaskAnswer(BaseModel):
    """Финальный ответ на задачу"""
    answer: str = Field(description="Ответ без лишних символов на поставленный вопрос в олимпиадной задаче")
