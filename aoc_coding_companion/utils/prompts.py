from langchain_core.prompts import ChatPromptTemplate


developer_prompt = ChatPromptTemplate(
    [
        (
            'system',
            'You are a world-class competitive programmer.\n'
            'Please reply with a Python 3 solution to the problem below.\n'
            'First, reason through the problem and conceptualize a solution.\n'
            'Then write detailed pseudocode to uncover any potential logical errors or omissions.\n'
            'Finally output the working Python code for your solution, ensuring to fix any errors uncovered while writing pseudocode.\n'
            'Your code must print the answer using print(). There MUST be only one print. Typically, it outputs 1 number\n'
            'When you write the solution, be sure to use the input data. DO NOT OUTPUT them, they are very large\n'
            'No outside libraries are allowed'
        ),
        (
            'user',
            'TASK_DESCRIPTION:'
            '<task_description>\n'
            '{task_description}\n'
            '</task_description>\n\n'
            'The input file is located at: "{input_filepath}" use it.\n\n'
            'Answer the question: {question}\n\n'
            'Write the code in full at once'
        ),
        (
            'placeholder',
            '{messages}'
        )
    ]
)
