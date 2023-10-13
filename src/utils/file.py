import os


def delete_file(path: str, silent: bool = False):
    try:
        os.remove(path)
    except Exception:
        if not silent:
            raise


def check_directories(path: str):
    if not os.path.isdir(path):
        os.makedirs(path)
