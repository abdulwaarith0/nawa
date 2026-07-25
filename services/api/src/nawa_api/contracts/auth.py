"""Auth contracts: session identity, request inputs, and token response DTOs."""

from pydantic import BaseModel, Field

from nawa_api.contracts.common import is_email_syntax, is_phone_syntax  # noqa: F401 (re-exported)


class SessionUser(BaseModel):
    """The verified session identity carried in the request context. Built from
    JWT claims; `sub` is the user id as a string."""

    sub: str
    full_name: str
    language: str
    perms: list[str] = Field(default_factory=list)


class SignupInput(BaseModel):
    full_name: str = Field(min_length=1)
    email: str
    password: str = Field(min_length=8)
    language: str = "ar"
    username: str | None = None
    phone: str | None = None


class RequestAccessInput(BaseModel):
    full_name: str = Field(min_length=1)
    email: str
    organization: str | None = None
    reason: str | None = None


class LoginInput(BaseModel):
    identifier: str
    password: str


class ForgotPasswordInput(BaseModel):
    identifier: str


class ResetPasswordInput(BaseModel):
    identifier: str
    code: str
    new_password: str = Field(min_length=8)


class RefreshInput(BaseModel):
    refresh_token: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class UserDto(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    language: str
    is_active: bool
    effective: list[str] = Field(default_factory=list)
