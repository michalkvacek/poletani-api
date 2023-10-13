import re
from fastapi import HTTPException
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel, root_validator, Field
from database.models import User
from database.transaction import get_session
from passlib.hash import bcrypt


class RegistrationInput(BaseModel):
    email: str = Field(..., min_length=4)
    name: Optional[str]
    password: str

    @root_validator()
    def validate_email(cls, values):
        email = values.get("email") or ""

        if email and not re.match(r"(.+)@(.+)\..{2,6}", email):
            raise ValueError("Specified e-mail is not valid!")

        return values


class RegistrationEndpoint:
    async def on_post(self, user_data: RegistrationInput) -> User:
        query = select(User).filter_by(email=user_data.email)
        async with get_session() as db:
            existing_user = (await db.scalars(query)).first()

            if existing_user:
                raise HTTPException(status_code=422, detail="User already exists")

            model = await User.create(db, {
                "name": user_data.name,
                "email": user_data.email,
                "password_hashed": bcrypt.hash(user_data.password),
                "description": ""
            })
            return model.as_dict()
