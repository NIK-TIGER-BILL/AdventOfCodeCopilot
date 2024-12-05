from langchain_core.prompts import ChatPromptTemplate


developer_prompt = ChatPromptTemplate(
    [
        (
            'system',
            'Ты программист на языке python, который решает много олимпиадных задач.'
        ),
        (
            'user',
            'Напиши python код, который решит олимпиадную задачу.\n'
            'Файл с входными данными input.txt лежит по пути: "{input_filepath}" используй его.\n\n'
            '<task>\n'
            '{task_description}\n'
            '</task>\n\n'
            'Код который ты напишешь должен вывести ответ на вопрос: {question}\n\n'
            'ВАЖНО: тебе нужно написать только ответ без лишних символов и слов.'
        ),
        (
            'placeholder',
            '{messages}'
        )
    ]
)
