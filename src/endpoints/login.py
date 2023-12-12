from fastapi import HTTPException
from fastapi_jwt import JwtAuthorizationCredentials
from passlib.hash import bcrypt
from sqlalchemy import select
from starlette.responses import Response
from database.models import User
from database.transaction import get_session
from endpoints.base import AuthEndpoint
from pydantic import BaseModel


class LoginInput(BaseModel):
    email: str
    password: str


class LoginEndpoint(AuthEndpoint):
    async def on_post(self, user_data: LoginInput, resp: Response) -> dict:
        query = select(User).filter_by(email=user_data.email)

        async with get_session() as db:
            logged_user = (await db.scalars(query)).first()
            if not logged_user:
                raise HTTPException(status_code=401, detail="Invalid user")

            user = logged_user.as_dict()
            password_hashed = logged_user.password_hashed

        if not bcrypt.verify(user_data.password, password_hashed):
            raise HTTPException(status_code=401, detail="Bad username or password")

        subject = {"id": user['id'], "email": user['email']}
        access_token = self.access_security.create_access_token(subject=subject)
        refresh_token = self.refresh_security.create_refresh_token(subject=subject)

        # self.access_security.set_access_cookie(resp, access_token)
        self.refresh_security.set_refresh_cookie(
            resp, refresh_token,
            expires_delta=self.refresh_security.refresh_expires_delta
        )

        return {
            "user": user,
            "access_token": access_token
        }


class LogoutEndpoint(AuthEndpoint):
    async def on_post(self, resp: Response):
        self.refresh_security.unset_refresh_cookie(resp)

        return {
            "logged_out": True
        }


class RefreshEndpoint(AuthEndpoint):

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
