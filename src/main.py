from datetime import timedelta
from fastapi import FastAPI, APIRouter, Depends, Security
from fastapi_jwt import JwtAuthorizationCredentials, JwtAccessBearerCookie, JwtRefreshBearerCookie
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, Response
from strawberry.fastapi import GraphQLRouter
from config import APP_SECRET_KEY, GRAPHIQL, APP_DEBUG
from dependencies.db import db_session
from endpoints.init_data import InitDataEndpoint
from endpoints.login import LoginEndpoint, LoginInput, MeEndpoint
from endpoints.registration import RegistrationInput, RegistrationEndpoint
from graphql_schema.schema import schema, GraphQLContext


class App:
    api_router = APIRouter(dependencies=[])
    access_security = JwtAccessBearerCookie(
        secret_key=APP_SECRET_KEY,
        auto_error=False,
        access_expires_delta=timedelta(hours=1)
    )
    refresh_security = JwtRefreshBearerCookie(
        secret_key=APP_SECRET_KEY,
        auto_error=True
    )

    def create_app(self):
        app = FastAPI()

        self.setup_exception_handlers(app)
        self.setup_middleware(app)
        self.setup_routes(app)

        return app

    @staticmethod
    def setup_exception_handlers(app: FastAPI):
        pass

    @staticmethod
    def setup_middleware(app: FastAPI):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_graphql_endpoint(self, app: FastAPI):
        if APP_DEBUG:
            @self.api_router.get("/graphql/autologin")
            async def autologin():
                access_token = self.access_security.create_access_token(subject={"id": 18, "name": "Franta Vomacka"})

                response = RedirectResponse(url="/graphql")
                self.access_security.set_access_cookie(response, access_token)

                return response

        def setup_graphql_context(
                credentials: JwtAuthorizationCredentials = Security(self.access_security),
                db: AsyncSession = Depends(db_session),
        ):

            return GraphQLContext(
                jwt_auth_credentials=credentials,
                user_id=credentials['id'],
                db=db,
                jwt=self.access_security
            )

        graphql_app = GraphQLRouter(
            schema,
            graphiql=GRAPHIQL,
            debug=APP_DEBUG,
            context_getter=setup_graphql_context
        )
        app.include_router(graphql_app, prefix="/graphql")

    def setup_routes(self, app: FastAPI):
        # protected endpoints
        @self.api_router.get("/me")
        async def me(
                db: AsyncSession = Depends(db_session),
                credentials: JwtAuthorizationCredentials = Security(self.access_security)
        ):
            return await MeEndpoint(db, credentials).on_get()

        # @app.post("/refresh")
        # def refresh(
        #         credentials: JwtAuthorizationCredentials = Security(refresh_security)
        # ):
        #     # Update access/refresh tokens pair
        #     # We can customize expires_delta when creating
        #     access_token = access_security.create_access_token(subject=credentials.subject)
        #     refresh_token = refresh_security.create_refresh_token(subject=credentials.subject,
        #     expires_delta=timedelta(days=2))
        #
        #     return {"access_token": access_token, "refresh_token": refresh_token}

        self.setup_graphql_endpoint(app)

        # public endpoints

        @self.api_router.post("/login")
        async def login(resp: Response, user: LoginInput, db: AsyncSession = Depends(db_session)):
            return await LoginEndpoint(db, self.access_security, self.refresh_security).on_post(user, resp)

        @self.api_router.post("/registration", status_code=201)
        async def registration(user: RegistrationInput, db: AsyncSession = Depends(db_session)):
            return await RegistrationEndpoint(db).on_post(user)

        # testing endpoint

        @self.api_router.get("/init-data")
        async def init_data(db: AsyncSession = Depends(db_session)):
            return await InitDataEndpoint(db).on_get()

        # musi byt na konci
        app.include_router(self.api_router)
