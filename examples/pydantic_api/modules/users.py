"""User feature: schema definitions and user endpoints."""

from pydantic import BaseModel, EmailStr

from flaxon.modules import FlaxonModule

users = FlaxonModule("users")


class CreateUser(BaseModel):
    name: str
    email: EmailStr
    age: int


@users.post("/")
async def create_user(user: CreateUser) -> CreateUser:
    """Validate and echo a user payload."""
    return user
