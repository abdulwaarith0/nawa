"""@audited decorator — wraps a handler and fire-and-forget schedules the
audit write in a finally. Never blocks, never fails the request."""

import asyncio
import functools
import time
import uuid

from nawa_api.contracts.errors import ApiError
from nawa_api.services.audit.create_audit_log import create_audit_log
from nawa_api.utils.request_context import get_session_user, request_id_var


def audited(*, action: str, target_type: str, capture_body: bool = False):
    def decorator(handler):
        @functools.wraps(handler)
        async def wrapper(*args, **kwargs):
            start, status = time.perf_counter(), 500
            try:
                result = await handler(*args, **kwargs)
                status = result.get("code", 200) if isinstance(result, dict) else 200
                return result
            except ApiError as err:
                status = err.code
                raise
            finally:
                session = get_session_user()
                actor_id = _to_uuid(session.sub) if session else None
                body = kwargs.get("body") if capture_body else None
                body_dump = body.model_dump() if hasattr(body, "model_dump") else body
                asyncio.create_task(
                    create_audit_log(
                        actor_id=actor_id,
                        action=action,
                        target_type=target_type,
                        status_code=status,
                        duration_ms=int((time.perf_counter() - start) * 1000),
                        request_id=request_id_var.get(),
                        body=body_dump,
                    )
                )

        return wrapper

    return decorator


def _to_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None
