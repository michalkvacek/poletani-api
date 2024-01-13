import os
import re
import uuid
from strawberry.file_uploads import Upload

from utils.file import check_directories


async def handle_file_upload(file: Upload, path: str, filename_maxlength: int = 64, uid_prefix: bool = True, overwrite: bool = True) -> str:
    check_directories(path)

    prefix = f"{uuid.uuid4()}-" if uid_prefix else ""
    filename = f"{prefix}{file.filename}"[-1 * filename_maxlength:]

    # sanitize filename
    filename = re.sub('[^\w_. -]', '', filename).replace(" ", "-")

    target_path = f"{path}/{filename}"

    if os.path.exists(target_path) and not overwrite:
        raise FileExistsError(f"File {filename} already exists")

    content = await file.read()
    image = open(target_path, "wb")
    image.write(content)
    image.close()

    return filename
