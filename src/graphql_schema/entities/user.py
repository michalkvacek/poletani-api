import strawberry
from sqlalchemy import select
from database.models import User
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type


@strawberry_sqlalchemy_type(User, exclude_fields=['password_hashed'])
class UserType:
    pass


@strawberry.type
class LoginResultType:
    logged_user = UserType
    access_token: str
    refresh_token: str


@strawberry.type
class UserQueries:

    @strawberry.field
    async def logged_user(root, info) -> UserType:
        query = select(User).filter_by(id=info.context.user_id)
        return (await info.context.db.scalars(query)).first()
