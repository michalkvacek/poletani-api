from functools import wraps
from typing import Optional
import strawberry
from graphql import GraphQLError
from passlib.hash import bcrypt
from sqlalchemy import select
from strawberry.file_uploads import Upload
from config import API_URL
from database import models
from database.models import User
from decorators.endpoints import authenticated_user_only
from decorators.error_logging import error_logging
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from upload_utils import handle_file_upload, delete_file, get_public_url, resize_image


@strawberry_sqlalchemy_type(User, exclude_fields=['password_hashed'])
class User:
    async def load_avatar_image_url(root):
        if not root.avatar_image_filename:
            return None

        return get_public_url(f"profile/{root.id}/{root.avatar_image_filename}")

    async def load_title_image_url(root):
        if not root.title_image_filename:
            return f"{API_URL}/static/default-title-image.jpg"

        return get_public_url(f"profile/{root.id}/{root.title_image_filename}")

    avatar_image_url: Optional[str] = strawberry.field(resolver=load_avatar_image_url)
    title_image_url: str = strawberry.field(resolver=load_title_image_url)


@strawberry.type
class UserQueries:
    @strawberry.field()
    @error_logging
    async def user(root, info, username: str) -> User:
        if len(username) == 0:
            raise GraphQLError("Username not set!")

        return (await info.context.db.scalars(select(models.User).filter_by(public_username=username))).one()

    @strawberry.field()
    @authenticated_user_only()
    @error_logging
    async def logged_user(root, info) -> User:
        user = (await info.context.db.scalars(
            select(models.User).filter_by(id=info.context.user_id)
        )).one()

        print(user)
        return user


@strawberry.type
class EditUserMutation:
    @strawberry_sqlalchemy_input(
        models.User,
        exclude_fields=['id', 'email', 'avatar_image_filename', 'password_hashed', 'title_image_filename'],
        all_optional=True
    )
    class EditUserInput:
        old_password: Optional[str] = None
        new_password: Optional[str] = None
        avatar_image: Optional[Upload] = None
        title_image: Optional[Upload] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_logged_user(root, info, input: EditUserInput) -> User:
        user = (await info.context.db.scalars(
            select(models.User).filter_by(id=info.context.user_id)
        )).one()

        user_image_path = f"/app/uploads/profile/{user.id}"
        data = input.to_dict()
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

        return await models.User.update(info.context.db, obj=user, data=data)
