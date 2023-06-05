import dataclasses
import strawberry
from fastapi_jwt import JwtAuthorizationCredentials
from fastapi_jwt.jwt import JwtAccessBearerCookie
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.extensions import SchemaExtension
from strawberry.fastapi import BaseContext
from .mutation import Mutation
from .query import Query


# Toto se da kdyztak pouzit jako extension do Schema
# class SQLAlchemySession(Extension):
#     def on_request_start(self):
#         session = async_session()
#         print(self.execution_context.context)
#         self.execution_context.context["db"] = session
#
#     async def on_request_end(self):
#         await self.execution_context.context["db"].close()

class LoggingExtension(SchemaExtension):
    def on_request_start(self):
        print("request start")

    async def on_request_end(self):
        print("request end")


@dataclasses.dataclass
class GraphQLContext(BaseContext):
    db: AsyncSession
    user_id: int
    jwt_auth_credentials: JwtAuthorizationCredentials
    jwt: JwtAccessBearerCookie


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[LoggingExtension]
)
