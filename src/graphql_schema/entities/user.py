from typing import Optional, TYPE_CHECKING
import strawberry
from graphql import GraphQLError
from passlib.hash import bcrypt
from sqlalchemy import select
from strawberry.file_uploads import Upload
from database import models
from decorators.endpoints import authenticated_user_only
from decorators.error_logging import error_logging
from dependencies.db import get_session
from upload_utils import handle_file_upload, delete_file, resize_image
from graphql_schema.entities.types.types import User

if TYPE_CHECKING:
    pass


@strawberry.type
class UserQueries:
    @strawberry.field()
    @error_logging
    async def user(root, info, username: str) -> User:
        if len(username) == 0:
            raise GraphQLError("Username not set!")

        async with get_session() as db:
            user_model = (await db.scalars(select(models.User).filter_by(public_username=username))).one()
            user = User(**user_model.as_dict())

        return user

    @strawberry.field()
    @authenticated_user_only()
    @error_logging
    async def logged_user(root, info) -> User:
        async with get_session() as db:
            user_model = (await db.scalars(
                select(models.User).filter_by(id=info.context.user_id)
            )).one()

            return User(**user_model.as_dict())


@strawberry.type
class EditUserMutation:
    @strawberry.input
    class EditUserInput:
        name: Optional[str] = None
        description: Optional[str] = None
        public_username: Optional[str] = None
        old_password: Optional[str] = None
        new_password: Optional[str] = None
        avatar_image: Optional[Upload] = None
        title_image: Optional[Upload] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_logged_user(root, info, input: EditUserInput) -> User:
        async with get_session() as db:
            user = (await db.scalars(
                select(models.User).filter_by(id=info.context.user_id)
            )).one()

            user_image_path = f"/app/uploads/profile/{user.id}"
            data = {
                key: getattr(input, key)
                for key in ("name", "description", "public_username")
                if getattr(input, key) is not None
            }
            if input.avatar_image:
                if user.avatar_image_filename:
                    delete_file(f"{user_image_path}/{user.avatar_image_filename}", silent=True)

                data['avatar_image_filename'] = await handle_file_upload(input.avatar_image, user_image_path)
                info.context.background_tasks.add_task(
                    resize_image, path=user_image_path, filename=data['avatar_image_filename'], new_width=400
                )

            if input.title_image:
                if user.title_image_filename:
                    delete_file(f"{user_image_path}/{user.title_image_filename}", silent=True)

                data['title_image_filename'] = await handle_file_upload(input.title_image, user_image_path)
                info.context.background_tasks.add_task(
                    resize_image, path=user_image_path, filename=data['title_image_filename'], new_width=800
                )

            if input.old_password and input.new_password:
                if not bcrypt.verify(input.old_password, user.password_hashed):
                    raise GraphQLError("Bad password")

                data['password_hashed'] = bcrypt.hash(input.new_password)

            user_model = await models.User.update(db, obj=user, data=data)
            return User(**user_model.as_dict())
