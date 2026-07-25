import uuid

import pytest
import pytest_asyncio

from nawa_api.contracts.auth import RequestAccessInput
from nawa_api.contracts.errors import ApiError
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.iam.list_user_group_ids_db import list_user_group_ids_db
from nawa_api.db.membership_requests.create_membership_request_db import (
    create_membership_request_db,
)
from nawa_api.db.membership_requests.list_membership_requests_db import (
    list_membership_requests_db,
)
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db.users.get_user_by_email_db import get_user_by_email_db
from nawa_api.runtime.redis import get_redis
from nawa_api.services.iam.seed_defaults import seed_defaults
from nawa_api.services.membership_requests.approve_membership_request import (
    approve_membership_request,
)
from nawa_api.services.membership_requests.list_membership_requests import (
    list_membership_requests,
)
from nawa_api.services.membership_requests.reject_membership_request import (
    reject_membership_request,
)
from nawa_api.services.membership_requests.submit_membership_request import (
    submit_membership_request,
)
from nawa_api.utils.password import hash_password


async def _reviewer(session):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    return await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash="hashed",
        full_name="Reviewer",
        session=session,
    )


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    """Binds the db-layer's session_factory to this test's transaction so
    service-layer calls (which open their own sessions) see the same rows."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    await seed_defaults()
    redis = get_redis()
    await redis.flushdb()
    yield db_session
    await redis.flushdb()


@pytest.mark.asyncio
async def test_submit_creates_a_pending_request(bound):
    await submit_membership_request(
        RequestAccessInput(full_name="Alice Founder", email="alice@example.com", reason="join")
    )
    rows = await list_membership_requests_db(session=bound)
    created = next(r for r in rows if r.email == "alice@example.com")
    assert created.status == "pending"


@pytest.mark.asyncio
async def test_submit_is_non_enumerable_when_email_already_has_an_account(bound):
    await create_user_db(
        email="existing@example.com",
        username="existing",
        password_hash="hashed",
        full_name="Existing User",
        session=bound,
    )
    await bound.commit()
    # Returns None either way — no exception, no signal the email exists.
    result = await submit_membership_request(
        RequestAccessInput(full_name="Someone", email="existing@example.com")
    )
    assert result is None
    # No request row created for an email that already has an account.
    rows = await list_membership_requests_db(session=bound)
    assert not any(r.email == "existing@example.com" for r in rows)


@pytest.mark.asyncio
async def test_list_membership_requests_returns_dtos(bound):
    await create_membership_request_db(
        full_name="Bob", email="bob@example.com", organization="Acme", session=bound
    )
    await bound.commit()
    items = await list_membership_requests(status="pending")
    created = next(i for i in items if i["email"] == "bob@example.com")
    assert created["organization"] == "Acme"
    assert created["status"] == "pending"


@pytest.mark.asyncio
async def test_approve_creates_user_joins_members_and_issues_reset_code(bound):
    request = await create_membership_request_db(
        full_name="Carol Founder", email="carol@example.com", session=bound
    )
    reviewer = await create_user_db(
        email="reviewer1@example.com",
        username="reviewer1",
        password_hash=hash_password("password123"),
        full_name="Reviewer",
        session=bound,
    )
    await bound.commit()

    dto = await approve_membership_request(request_id=request.id, reviewer_user_id=reviewer.id)

    assert dto["status"] == "approved"
    assert dto["reviewed_by_user_id"] == str(reviewer.id)
    assert dto["reviewed_at"] is not None

    created_user = await get_user_by_email_db(email="carol@example.com", session=bound)
    assert created_user is not None

    members = await get_group_by_name_db(name="Members", session=bound)
    group_ids = await list_user_group_ids_db(user_id=created_user.id, session=bound)
    assert members.id in group_ids

    # The reused password-reset mechanism stored a real code for this email.
    code = await get_redis().get("auth:reset:carol@example.com")
    assert code is not None


@pytest.mark.asyncio
async def test_approve_missing_request_raises_not_found(bound):
    with pytest.raises(ApiError) as exc:
        await approve_membership_request(request_id=uuid.uuid4(), reviewer_user_id=uuid.uuid4())
    assert exc.value.code == 404


@pytest.mark.asyncio
async def test_approve_already_reviewed_request_conflicts(bound):
    request = await create_membership_request_db(
        full_name="Dan", email="dan@example.com", session=bound
    )
    reviewer = await _reviewer(bound)
    await bound.commit()
    await approve_membership_request(request_id=request.id, reviewer_user_id=reviewer.id)
    with pytest.raises(ApiError) as exc:
        await approve_membership_request(request_id=request.id, reviewer_user_id=reviewer.id)
    assert exc.value.code == 409


@pytest.mark.asyncio
async def test_approve_conflicts_when_email_already_has_an_account(bound):
    await create_user_db(
        email="taken@example.com",
        username="taken",
        password_hash="hashed",
        full_name="Taken",
        session=bound,
    )
    request = await create_membership_request_db(
        full_name="Erin", email="taken@example.com", session=bound
    )
    await bound.commit()
    with pytest.raises(ApiError) as exc:
        await approve_membership_request(request_id=request.id, reviewer_user_id=uuid.uuid4())
    assert exc.value.code == 409


@pytest.mark.asyncio
async def test_reject_marks_request_rejected(bound):
    request = await create_membership_request_db(
        full_name="Frank", email="frank@example.com", session=bound
    )
    reviewer = await _reviewer(bound)
    await bound.commit()
    dto = await reject_membership_request(request_id=request.id, reviewer_user_id=reviewer.id)
    assert dto["status"] == "rejected"
    assert dto["reviewed_by_user_id"] == str(reviewer.id)
    assert dto["reviewed_at"] is not None

    # No user is created on rejection (fresh session — `bound`'s identity map
    # would otherwise return its stale, pre-commit view of this row).
    assert await get_user_by_email_db(email="frank@example.com") is None


@pytest.mark.asyncio
async def test_reject_missing_request_raises_not_found(bound):
    with pytest.raises(ApiError) as exc:
        await reject_membership_request(request_id=uuid.uuid4(), reviewer_user_id=uuid.uuid4())
    assert exc.value.code == 404


@pytest.mark.asyncio
async def test_reject_already_reviewed_request_conflicts(bound):
    request = await create_membership_request_db(
        full_name="Grace", email="grace@example.com", session=bound
    )
    reviewer = await _reviewer(bound)
    await bound.commit()
    await reject_membership_request(request_id=request.id, reviewer_user_id=reviewer.id)
    with pytest.raises(ApiError) as exc:
        await reject_membership_request(request_id=request.id, reviewer_user_id=reviewer.id)
    assert exc.value.code == 409
