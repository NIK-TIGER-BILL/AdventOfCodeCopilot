from pydantic import BaseModel, Field


class PythonREPL(BaseModel):
    """Python-интерпретатор. Используйте его для выполнения команд на Python"""
    query: str = Field(description="Фрагмент python кода для решение задачи с выводом результата в консоль")


class TaskAnswer(BaseModel):
    """Финальный ответ на задачу"""
    answer: str = Field(description='Ответ на поставленный вопрос в олимпиадной задаче. '
                                    'НЕ ПОВТОРЯЙСЯ. '
                                    'Если ты ранее отвечал такой ответ, не дублируй его а попробуй переписать код')
