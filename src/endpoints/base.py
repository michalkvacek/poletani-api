from fastapi_jwt.jwt import JwtAccess, JwtRefresh


class BaseEndpoint:
    def __init__(self, db):
        self.db = db


class AuthEndpoint:
    def __init__(self, *args, **kwargs):
        self.access_security: JwtAccess = kwargs.pop("access_token")
        self.refresh_security: JwtRefresh = kwargs.pop("refresh_token")
        super().__init__(*args, **kwargs)
