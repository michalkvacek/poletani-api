import uuid
from strawberry.file_uploads import Upload

from utils.file import check_directories


async def handle_file_upload(file: Upload, path: str) -> str:
    check_directories(path)

    filename = f"{uuid.uuid4()}-{file.filename}"

    content = await file.read()
    image = open(path + "/" + filename, "wb")
    image.write(content)
    image.close()

    return filename
