import uuid

from sqlalchemy import func, select

from nawa_api.ai.pii import PiiMapping
from nawa_api.db.pii.get_token_map_db import get_token_map_db
from nawa_api.db.pii.upsert_token_map_db import upsert_token_map_db
from nawa_api.models.ai import PiiTokenMap
from nawa_api.services.pii import get_pii_mapping, upsert_pii_mapping


async def test_upsert_then_get_roundtrips_tokens(db_session):
    subject_id = uuid.uuid4()
    tokens = {"PERSON_1": "Amina", "EMAIL_1": "a@x.io"}
    await upsert_token_map_db(
        subject_type="application", subject_id=subject_id, tokens=tokens, session=db_session
    )
    row = await get_token_map_db(
        subject_type="application", subject_id=subject_id, session=db_session
    )
    assert row is not None
    assert row.tokens == tokens


async def test_upsert_is_idempotent_on_subject_unique(db_session):
    subject_id = uuid.uuid4()
    await upsert_token_map_db(
        subject_type="application",
        subject_id=subject_id,
        tokens={"PERSON_1": "A"},
        session=db_session,
    )
    await upsert_token_map_db(
        subject_type="application",
        subject_id=subject_id,
        tokens={"PERSON_1": "A", "PERSON_2": "B"},
        session=db_session,
    )
    count = await db_session.scalar(
        select(func.count())
        .select_from(PiiTokenMap)
        .where(PiiTokenMap.subject_type == "application", PiiTokenMap.subject_id == subject_id)
    )
    assert count == 1
    row = await get_token_map_db(
        subject_type="application", subject_id=subject_id, session=db_session
    )
    assert row.tokens == {"PERSON_1": "A", "PERSON_2": "B"}


async def test_get_missing_subject_returns_none(db_session):
    row = await get_token_map_db(
        subject_type="application", subject_id=uuid.uuid4(), session=db_session
    )
    assert row is None


async def test_service_get_returns_empty_mapping_when_absent(monkeypatch):
    import importlib

    get_mod = importlib.import_module("nawa_api.services.pii.get_pii_mapping")

    async def fake_get(**_kwargs):
        return None

    monkeypatch.setattr(get_mod, "get_token_map_db", fake_get)
    mapping = await get_pii_mapping(subject_type="application", subject_id=uuid.uuid4())
    assert isinstance(mapping, PiiMapping)
    assert mapping.tokens == {}


async def test_service_upsert_returns_persisted_tokens(monkeypatch):
    import importlib

    upsert_mod = importlib.import_module("nawa_api.services.pii.upsert_pii_mapping")

    class Row:
        tokens = {"PERSON_1": "Amina"}

    async def fake_upsert(**_kwargs):
        return Row()

    monkeypatch.setattr(upsert_mod, "upsert_token_map_db", fake_upsert)
    out = await upsert_pii_mapping(
        subject_type="application",
        subject_id=uuid.uuid4(),
        mapping=PiiMapping(tokens={"PERSON_1": "Amina"}),
    )
    assert out.tokens == {"PERSON_1": "Amina"}
