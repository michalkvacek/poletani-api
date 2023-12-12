import sentry_sdk
from datetime import timedelta
from typing import Optional
from fastapi import FastAPI, APIRouter, Depends, Security, HTTPException
from fastapi_jwt import JwtAuthorizationCredentials, JwtAccessBearerCookie, JwtRefreshBearerCookie
from graphql import GraphQLError
from sqlalchemy import select
from starlette.background import BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, Response
from starlette.staticfiles import StaticFiles
from strawberry.fastapi import GraphQLRouter
from config import APP_SECRET_KEY, GRAPHIQL, APP_DEBUG, ALLOW_CORS_ORIGINS, SENTRY_DSN, REFRESH_TOKEN_VALIDITY_DAYS
from database import models, async_session
from endpoints.login import LoginEndpoint, LoginInput, RefreshEndpoint, LogoutEndpoint
from endpoints.photo_editor_preview import PhotoEditorEndpoint
from endpoints.registration import RegistrationInput, RegistrationEndpoint
from graphql_schema.schema import schema, GraphQLContext


class App:
    api_router = APIRouter(dependencies=[])
    access_security = JwtAccessBearerCookie(
        secret_key=APP_SECRET_KEY,
        auto_error=False,
    )
    refresh_security = JwtRefreshBearerCookie(
        secret_key=APP_SECRET_KEY,
        auto_error=True,
        refresh_expires_delta=timedelta(days=REFRESH_TOKEN_VALIDITY_DAYS),
    )

    def create_app(self):
        if SENTRY_DSN:
            sentry_sdk.init(
                dsn=SENTRY_DSN,
                enable_tracing=True,
                ignore_errors=[GraphQLError, HTTPException]
            )

        app = FastAPI()

        self.setup_exception_handlers(app)
        self.setup_middleware(app)
        self.setup_static_paths(app)
        self.setup_routes(app)

        return app

    @staticmethod
    def setup_exception_handlers(app: FastAPI):
        pass

    @staticmethod
    def setup_middleware(app: FastAPI):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ALLOW_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @staticmethod
    def setup_static_paths(app: FastAPI):
        app.mount("/uploads", StaticFiles(directory="/app/uploads"), name="uploads")
        app.mount("/static", StaticFiles(directory="/app/static"), name="static")

    def setup_graphql_endpoint(self, app: FastAPI):
        async def setup_graphql_context(credentials: JwtAuthorizationCredentials = Security(self.access_security)):
            user_id = credentials['id'] if credentials else None
            organization_ids = set()

            if user_id:
                async with async_session() as db:
                    organization_ids = set((await db.scalars(
                        select(models.user_is_in_organization.c.organization_id)
                        .filter(models.user_is_in_organization.c.user_id == user_id)
                    )).all())

            return GraphQLContext(
                user_id=user_id,
                organization_ids=organization_ids,
                jwt_auth_credentials=credentials,
                jwt=self.access_security,
                background_tasks=Depends(BackgroundTasks)
            )

        graphql_app = GraphQLRouter(
            schema,
            graphiql=GRAPHIQL,
            debug=APP_DEBUG,
            context_getter=setup_graphql_context
        )
        app.include_router(graphql_app, prefix="/graphql")

    def setup_routes(self, app: FastAPI):
        self.setup_graphql_endpoint(app)

        if APP_DEBUG:
            @self.api_router.get("/graphql/autologin")
            async def autologin():
                access_token = self.access_security.create_access_token(subject={"id": 6, "name": "Franta Vomacka"})

                response = RedirectResponse(url="/graphql")
                self.access_security.set_access_cookie(response, access_token, expires_delta=timedelta(days=14))

                return response

        @self.api_router.post("/refresh")
        async def refresh(
                resp: Response,
                credentials: JwtAuthorizationCredentials = Security(self.refresh_security)
        ):
            return await RefreshEndpoint(
                access_token=self.access_security,
                refresh_token=self.refresh_security
            ).on_post(resp, credentials)

        @self.api_router.post("/login")
        async def login(resp: Response, user: LoginInput):
            return await LoginEndpoint(
                access_token=self.access_security,
                refresh_token=self.refresh_security
            ).on_post(user, resp)

        @self.api_router.post("/logout")
        async def logout(resp: Response):
            return await LogoutEndpoint(
                access_token=self.access_security,
                refresh_token=self.refresh_security
            ).on_post(resp)

        @self.api_router.get("/photo/editor-preview/{photo_id}")
        async def photo_editor_preview(
                photo_id: int,
                brightness: Optional[float] = None,
                contrast: Optional[float] = None,
                saturation: Optional[float] = None,
                sharpness: Optional[float] = None,
                rotate: Optional[float] = None,
                crop_left: Optional[float] = None,
                crop_top: Optional[float] = None,
                crop_width: Optional[float] = None,
                crop_height: Optional[float] = None,
        ):
            return await PhotoEditorEndpoint(
                access_token=self.access_security,
                refresh_token=self.refresh_security
            ).show_preview(
                photo_id=photo_id,
                logged_user_id=0,
                saturation=saturation,
                brightness=brightness,
                contrast=contrast,
                sharpness=sharpness,
                crop_top=crop_top,
                crop_left=crop_left,
                crop_height=crop_height,
                crop_width=crop_width,
                rotate=rotate,
            )

        @self.api_router.post("/registration", status_code=201)
        async def registration(user: RegistrationInput):
            return await RegistrationEndpoint().on_post(user)

        # musi byt na konci
        app.include_router(self.api_router)
