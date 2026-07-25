from fastapi import APIRouter, Request

from nawa_api.contracts.auth import (
    ForgotPasswordInput,
    LoginInput,
    RefreshInput,
    RequestAccessInput,
    ResetPasswordInput,
    SignupInput,
)
from nawa_api.middleware.audit import audited
from nawa_api.services.auth.get_me import get_me
from nawa_api.services.auth.login import login as login_service
from nawa_api.services.auth.logout import logout as logout_service
from nawa_api.services.auth.password_reset import forgot_password, reset_password
from nawa_api.services.auth.refresh import refresh as refresh_service
from nawa_api.services.auth.signup import signup as signup_service
from nawa_api.services.membership_requests.submit_membership_request import (
    submit_membership_request,
)
from nawa_api.utils.envelope import ok
from nawa_api.utils.request_context import REFRESH_COOKIE_NAME

router = APIRouter(prefix="/auth", tags=["auth"])


def _is_bearer(request: Request) -> bool:
    return "x-client" in request.headers and "x-device-id" in request.headers


def _device_id(request: Request) -> str | None:
    return request.headers.get("x-device-id")


def _refresh_from_request(request: Request, body_token: str | None) -> str | None:
    return body_token or request.cookies.get(REFRESH_COOKIE_NAME)


@router.post("/signup")
@audited(action="auth.signup", target_type="user", capture_body=False)
async def signup_route(body: SignupInput, request: Request):
    data = await signup_service(body, bearer=_is_bearer(request), device_id=_device_id(request))
    return ok(data)


@router.post("/request-access")
@audited(action="auth.request_access", target_type="membership_request", capture_body=False)
async def request_access_route(body: RequestAccessInput):
    await submit_membership_request(body)
    return ok(None)


@router.post("/login")
@audited(action="auth.login", target_type="user")
async def login_route(body: LoginInput, request: Request):
    data = await login_service(body, bearer=_is_bearer(request), device_id=_device_id(request))
    return ok(data)


@router.post("/refresh")
async def refresh_route(request: Request, body: RefreshInput | None = None):
    token = _refresh_from_request(request, body.refresh_token if body else None)
    data = await refresh_service(token_plain=token, bearer=_is_bearer(request))
    return ok(data)


@router.post("/logout")
async def logout_route(request: Request, body: RefreshInput | None = None):
    token = _refresh_from_request(request, body.refresh_token if body else None)
    await logout_service(refresh_token_plain=token)
    return ok(None)


@router.get("/me")
async def me_route():
    return ok(await get_me())


@router.post("/forgot-password")
async def forgot_password_route(body: ForgotPasswordInput):
    await forgot_password(body)
    return ok(None)


@router.post("/reset-password")
@audited(action="auth.password_reset", target_type="user")
async def reset_password_route(body: ResetPasswordInput):
    await reset_password(body)
    return ok(None)
