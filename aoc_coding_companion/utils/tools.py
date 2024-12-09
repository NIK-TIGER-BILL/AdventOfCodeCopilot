import sys
from io import StringIO
from multiprocessing import Process, Queue


def run_code(queue, code):
    old_stdout = sys.stdout
    mystdout = StringIO()
    sys.stdout = mystdout

    try:
        exec(code, {})
        result = mystdout.getvalue()
    except Exception as e:
        result = repr(e)

    sys.stdout = old_stdout
    queue.put(result)


def run_python_code_with_timeout(code: str, timeout: int) -> str:
    queue = Queue()
    process = Process(target=run_code, args=(queue, code))
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        raise TimeoutError(f'Код работает больше {timeout} секунд')

    return queue.get()