import pytest

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.create_group_db import create_group_db
from nawa_api.db.iam.create_policy_db import create_policy_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.iam.get_policy_by_name_db import get_policy_by_name_db
from nawa_api.db.iam.list_groups_db import list_groups_db
from nawa_api.db.iam.list_policies_db import list_policies_db
from nawa_api.db.iam.list_user_group_ids_db import list_user_group_ids_db
from nawa_api.db.users.create_user_db import create_user_db


@pytest.mark.asyncio
async def test_create_and_get_policy_round_trips(db_session):
    created = await create_policy_db(
        name="AdministratorAccess",
        statements=[{"effect": "Allow", "actions": ["*"]}],
        managed=True,
        session=db_session,
    )
    assert created is not None
    fetched = await get_policy_by_name_db(name="AdministratorAccess", session=db_session)
    assert fetched is not None
    assert fetched.statements == [{"effect": "Allow", "actions": ["*"]}]


@pytest.mark.asyncio
async def test_list_policies_db_returns_created_rows(db_session):
    await create_policy_db(name="MembersBaseline", statements=[], session=db_session)
    rows = await list_policies_db(session=db_session)
    assert any(p.name == "MembersBaseline" for p in rows)


@pytest.mark.asyncio
async def test_create_and_get_group_round_trips(db_session):
    policy = await create_policy_db(name="FounderAccess", statements=[], session=db_session)
    created = await create_group_db(
        name="Founders", policy_ids=[policy.id], managed=True, session=db_session
    )
    assert created is not None
    fetched = await get_group_by_name_db(name="Founders", session=db_session)
    assert fetched is not None
    assert fetched.policy_ids == [policy.id]


@pytest.mark.asyncio
async def test_list_groups_db_returns_created_rows(db_session):
    await create_group_db(name="Mentors", session=db_session)
    rows = await list_groups_db(session=db_session)
    assert any(g.name == "Mentors" for g in rows)


@pytest.mark.asyncio
async def test_add_group_member_and_list_user_group_ids(db_session):
    user = await create_user_db(
        email="member@example.com",
        username="membertest",
        password_hash="hashed",
        full_name="Member Test",
        session=db_session,
    )
    group = await create_group_db(name="Members", session=db_session)
    membership = await add_group_member_db(group_id=group.id, user_id=user.id, session=db_session)
    assert membership is not None

    group_ids = await list_user_group_ids_db(user_id=user.id, session=db_session)
    assert group.id in group_ids


@pytest.mark.asyncio
async def test_get_policy_by_name_db_returns_none_for_missing_name(db_session):
    result = await get_policy_by_name_db(name="DoesNotExist", session=db_session)
    assert result is None
