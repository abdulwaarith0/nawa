import asyncio

import pytest

from nawa_api.contracts.auth import SessionUser
from nawa_api.utils import request_context as rc


def test_get_session_user_defaults_to_none():
    rc.session_var.set(None)
    assert rc.get_session_user() is None


def test_set_and_get_session_user():
    user = SessionUser(sub="u1", full_name="A", language="en", perms=[])
    token = rc.session_var.set(user)
    try:
        assert rc.get_session_user() is user
    finally:
        rc.session_var.reset(token)


def test_get_logger_falls_back_outside_request():
    rc.logger_var.set(None)
    logger = rc.get_logger()
    assert logger is not None


def test_cookie_queue_accumulates_ops():
    rc.pending_cookies_var.set([])
    rc.issue_session_cookie("jwt-token")
    rc.issue_refresh_cookie("refresh-token")
    ops = rc.pending_cookies_var.get()
    assert len(ops) == 2
    assert ops[0].name == "nw_session"
    assert ops[0].value == "jwt-token"
    assert ops[1].name == "nw_refresh"


def test_revoke_session_cookie_queues_deletions():
    rc.pending_cookies_var.set([])
    rc.revoke_session_cookie()
    ops = rc.pending_cookies_var.get()
    assert len(ops) == 2
    assert all(op.value is None for op in ops)


@pytest.mark.asyncio
async def test_context_isolation_across_concurrent_tasks():
    results = {}

    async def worker(name: str):
        user = SessionUser(sub=name, full_name=name, language="en", perms=[])
        rc.session_var.set(user)
        await asyncio.sleep(0.01)
        results[name] = rc.get_session_user().sub

    await asyncio.gather(worker("a"), worker("b"))
    # Each task's contextvar mutation stays isolated to that task.
    assert results == {"a": "a", "b": "b"}
