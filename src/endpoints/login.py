from fastapi import HTTPException
from fastapi_jwt import JwtAuthorizationCredentials
from fastapi_jwt.jwt import JwtAccess, JwtRefresh
from passlib.hash import bcrypt
from sqlalchemy import select
from starlette.responses import Response

from database.models import User
from endpoints.base import BaseEndpoint
from pydantic import BaseModel


class LoginInput(BaseModel):
    email: str
    password: str


class LoginEndpoint(BaseEndpoint):

    def __init__(self, db, access_token: JwtAccess, refresh_token: JwtRefresh):
        super().__init__(db)
        self.access_security = access_token
        self.refresh_security = refresh_token

    async def on_post(self, user_data: LoginInput, resp: Response) -> dict:
        query = select(User).filter_by(email=user_data.email)
        logged_user = (await self.db.scalars(query)).first()

        if not logged_user:
            raise HTTPException(status_code=401, detail="Invalid user")

        if not bcrypt.verify(user_data.password, logged_user.password_hashed):
            raise HTTPException(status_code=401, detail="Bad username or password")

        subject = {"id": logged_user.id, "email": logged_user.email}
        access_token = self.access_security.create_access_token(subject=subject)
        refresh_token = self.refresh_security.create_refresh_token(subject=subject)

        # self.access_security.set_access_cookie(resp, access_token)
        self.refresh_security.set_refresh_cookie(
            resp, refresh_token,
            expires_delta=self.refresh_security.refresh_expires_delta
        )

        return {
            "user": logged_user.as_dict(),
            "access_token": access_token,
            "access_token_validity": self.access_security.access_expires_delta.total_seconds(),
        }

class RefreshEndpoint(BaseEndpoint):
    def __init__(self, access_token: JwtAccess, refresh_token: JwtRefresh):
        super().__init__(db=None)
        self.access_security = access_token
        self.refresh_security = refresh_token

    async def on_post(self, resp: Response, credentials: JwtAuthorizationCredentials):
        access_token = self.access_security.create_access_token(
            subject=credentials.subject,
            expires_delta=self.access_security.access_expires_delta
        )
        refresh_token = self.refresh_security.create_refresh_token(
            subject=credentials.subject,
            expires_delta=self.refresh_security.refresh_expires_delta
        )

        self.refresh_security.set_refresh_cookie(
            resp, refresh_token,
            expires_delta=self.refresh_security.refresh_expires_delta
        )

        return {
            "access_token": access_token,
            "access_token_validity": self.access_security.access_expires_delta.total_seconds(),
        }


class MeEndpoint(BaseEndpoint):

    async def on_get(self, credentials) -> dict:
        if not credentials:
            raise HTTPException(status_code=401)

        query = select(User).filter_by(id=credentials['id'])
        user = (await self.db.scalars(query)).first()

        return user.as_dict()
