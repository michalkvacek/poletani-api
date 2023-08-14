from fastapi_jwt.jwt import JwtAccess, JwtRefresh

class BaseEndpoint:
    def __init__(self, *args, **kwargs):
        self.db = kwargs.get("db")
        super().__init__(*args, **kwargs)


class AuthEndpoint:
    def __init__(self, *args, **kwargs):
        self.access_security: JwtAccess = kwargs.get("access_token")
        self.refresh_security: JwtRefresh = kwargs.get("refresh_token")
        super().__init__()
