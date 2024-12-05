import sys
from io import StringIO


def run_python_code(code: str) -> str:
    old_stdout = sys.stdout
    mystdout = StringIO()
    sys.stdout = mystdout

    try:
        exec(code, {})
    except Exception as e:
        sys.stdout = old_stdout
        return repr(e)

    sys.stdout = old_stdout
    return mystdout.getvalue()
