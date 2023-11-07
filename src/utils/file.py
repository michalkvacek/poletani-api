import os


def delete_file(path: str, silent: bool = False):
    try:
        os.remove(path)
    except Exception:
        if not silent:
            raise


def check_directories(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
