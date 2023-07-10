import os
import uuid
from typing import Optional
from strawberry.file_uploads import Upload


def get_public_url(filename: Optional[str]):
    return f"http://localhost:8999/{filename}" if filename else None


def check_directories(path: str):
    if not os.path.isdir(path):
        os.makedirs(path)


async def handle_file_upload(file: Upload, path: str):
    check_directories(path)

    filename = f"{uuid.uuid4()}-{file.filename}"

    content = await file.read()
    image = open(path + "/" + filename, "wb")
    image.write(content)
    image.close()

    return filename


def delete_file(path: str, silent: bool = False):
    os.remove(path)
