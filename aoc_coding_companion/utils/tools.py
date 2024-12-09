import sys
from io import StringIO
import signal


class ExecTimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise ExecTimeoutException("Execution timed out")


def run_python_code_with_timeout(code: str, timeout: int) -> str:
    # Сохраняем старый обработчик сигналов
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)

    signal.alarm(timeout)  # Устанавливаем сигнал аларма на указанное количество секунд
    old_stdout = sys.stdout
    mystdout = StringIO()
    sys.stdout = mystdout

    try:
        exec(code, {})
        result = mystdout.getvalue()
    except ExecTimeoutException as e:
        raise e
    except Exception as e:
        result = repr(e)
    finally:
        sys.stdout = old_stdout
        signal.alarm(0)  # Отключаем сигнал алярма
        signal.signal(signal.SIGALRM, old_handler)  # Восстанавливаем старый обработчик сигналов

    return result


# Пример использования:
if __name__ == '__main__':
    code = "for i in range(10**8): pass"
    result = run_python_code_with_timeout(code, 12)
    print(result)
