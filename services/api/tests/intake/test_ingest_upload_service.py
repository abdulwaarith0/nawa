import uuid

import pytest
import pytest_asyncio

from nawa_api.contracts.errors import ERR_INVALID_FIELDS, ERR_NOT_FOUND, ApiError
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.redis import get_redis
from nawa_api.runtime.storage import get_storage_provider, reset_storage_provider_cache
from nawa_api.services.intake import ingest_upload as ingest_upload_mod
from nawa_api.services.intake.ingest_upload import (
    create_upload_and_applications,
    fan_out_processing,
    progress_key,
)
from nawa_api.utils.password import hash_password

_CSV = b"name,email,idea\nAmina,amina@x.io,Solar irrigation\nYusuf,yusuf@x.io,Water reuse\n"
_COLUMN_MAP = {"name": "applicant_name", "email": "applicant_email", "idea": "idea"}


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    reset_storage_provider_cache()
    yield db_session
    reset_storage_provider_cache()


async def _cycle(session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=session
    )
    return await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )


async def _user(session):
    email = f"{uuid.uuid4().hex[:8]}@x.io"
    return await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Uploader",
        session=session,
    )


@pytest.mark.asyncio
async def test_create_upload_and_applications_persists_rows_and_seeds_progress(bound):
    cycle = await _cycle(bound)
    uploader = await _user(bound)
    await bound.commit()

    outcome = await create_upload_and_applications(
        cycle_id=cycle.id,
        filename="batch.csv",
        content=_CSV,
        mime_type="text/csv",
        column_map=_COLUMN_MAP,
        uploaded_by_user_id=uploader.id,
    )

    assert outcome["row_count"] == 2
    assert len(outcome["application_ids"]) == 2

    application = await get_application_db(application_id=outcome["application_ids"][0])
    assert application is not None
    assert application.source_language == "en"
    assert application.status == "submitted"

    stored = get_storage_provider().get_object(
        f"intake/uploads/{cycle.id}/{outcome['upload_id']}/source.csv"
    )
    assert stored == _CSV

    progress = await get_redis().hgetall(progress_key(outcome["upload_id"]))
    assert int(progress["total"]) == 2
    assert int(progress["done"]) == 0


@pytest.mark.asyncio
async def test_create_upload_and_applications_raises_not_found_when_upload_row_write_fails(
    bound, monkeypatch
):
    cycle = await _cycle(bound)
    await bound.commit()

    async def fake_create_upload(**kwargs):
        return None

    monkeypatch.setattr(ingest_upload_mod, "create_application_upload_db", fake_create_upload)

    with pytest.raises(ApiError) as exc_info:
        await create_upload_and_applications(
            cycle_id=cycle.id,
            filename="batch.csv",
            content=_CSV,
            mime_type="text/csv",
            column_map=_COLUMN_MAP,
            uploaded_by_user_id=uuid.uuid4(),
        )
    assert exc_info.value == ERR_NOT_FOUND


@pytest.mark.asyncio
async def test_create_upload_and_applications_skips_rows_whose_write_fails(bound, monkeypatch):
    cycle = await _cycle(bound)
    uploader = await _user(bound)
    await bound.commit()

    async def fake_create_application(**kwargs):
        return None

    monkeypatch.setattr(ingest_upload_mod, "create_application_db", fake_create_application)

    outcome = await create_upload_and_applications(
        cycle_id=cycle.id,
        filename="batch.csv",
        content=_CSV,
        mime_type="text/csv",
        column_map=_COLUMN_MAP,
        uploaded_by_user_id=uploader.id,
    )

    assert outcome["application_ids"] == []
    assert outcome["row_count"] == 0


@pytest.mark.asyncio
async def test_create_upload_and_applications_missing_cycle_raises_not_found(bound):
    with pytest.raises(ApiError) as exc_info:
        await create_upload_and_applications(
            cycle_id=uuid.uuid4(),
            filename="batch.csv",
            content=_CSV,
            mime_type="text/csv",
            column_map=_COLUMN_MAP,
            uploaded_by_user_id=uuid.uuid4(),
        )
    assert exc_info.value == ERR_NOT_FOUND


@pytest.mark.asyncio
async def test_create_upload_and_applications_bad_column_map_raises_invalid_fields(bound):
    cycle = await _cycle(bound)
    await bound.commit()
    with pytest.raises(ApiError) as exc_info:
        await create_upload_and_applications(
            cycle_id=cycle.id,
            filename="batch.csv",
            content=_CSV,
            mime_type="text/csv",
            column_map={},  # no applicant_name/applicant_email mapped
            uploaded_by_user_id=uuid.uuid4(),
        )
    assert exc_info.value == ERR_INVALID_FIELDS


@pytest.mark.asyncio
async def test_fan_out_processing_chains_embed_and_dedup_after_normalize_success(monkeypatch):
    calls = []

    async def fake_normalize(*, application_id, upload_id, cycle_id):
        calls.append(("normalize", application_id))
        return "normalized"

    async def fake_embed(*, application_id):
        calls.append(("embed", application_id))
        return "embedded"

    async def fake_dedup(*, application_id):
        calls.append(("dedup", application_id))
        return 0

    monkeypatch.setattr(ingest_upload_mod, "normalize_application", fake_normalize)
    monkeypatch.setattr(ingest_upload_mod, "embed_application", fake_embed)
    monkeypatch.setattr(ingest_upload_mod, "dedup_scan", fake_dedup)

    aid = uuid.uuid4()
    await fan_out_processing(application_ids=[aid], upload_id=uuid.uuid4(), cycle_id=uuid.uuid4())

    assert calls == [("normalize", aid), ("embed", aid), ("dedup", aid)]


@pytest.mark.asyncio
async def test_fan_out_processing_accepts_no_upload_id_for_single_entry(monkeypatch):
    # services/intake/create_application.py's single-form-entry route has no
    # batch to track progress for — upload_id=None must still chain normally.
    calls = []

    async def fake_normalize(*, application_id, upload_id, cycle_id):
        calls.append(("normalize", application_id, upload_id))
        return "normalized"

    async def fake_embed(*, application_id):
        calls.append(("embed", application_id))
        return "embedded"

    async def fake_dedup(*, application_id):
        calls.append(("dedup", application_id))
        return 0

    monkeypatch.setattr(ingest_upload_mod, "normalize_application", fake_normalize)
    monkeypatch.setattr(ingest_upload_mod, "embed_application", fake_embed)
    monkeypatch.setattr(ingest_upload_mod, "dedup_scan", fake_dedup)

    aid = uuid.uuid4()
    await fan_out_processing(application_ids=[aid], upload_id=None, cycle_id=uuid.uuid4())

    assert calls == [("normalize", aid, None), ("embed", aid), ("dedup", aid)]


@pytest.mark.asyncio
async def test_fan_out_processing_skips_embed_when_normalize_fails(monkeypatch):
    calls = []

    async def fake_normalize(*, application_id, upload_id, cycle_id):
        return "normalize_failed"

    async def fake_embed(*, application_id):
        calls.append("embed")
        return "embedded"

    monkeypatch.setattr(ingest_upload_mod, "normalize_application", fake_normalize)
    monkeypatch.setattr(ingest_upload_mod, "embed_application", fake_embed)

    await fan_out_processing(
        application_ids=[uuid.uuid4()], upload_id=uuid.uuid4(), cycle_id=uuid.uuid4()
    )

    assert calls == []


@pytest.mark.asyncio
async def test_fan_out_processing_skips_dedup_when_embed_is_unchanged(monkeypatch):
    calls = []

    async def fake_normalize(*, application_id, upload_id, cycle_id):
        return "normalized"

    async def fake_embed(*, application_id):
        return "unchanged"

    async def fake_dedup(*, application_id):
        calls.append("dedup")
        return 0

    monkeypatch.setattr(ingest_upload_mod, "normalize_application", fake_normalize)
    monkeypatch.setattr(ingest_upload_mod, "embed_application", fake_embed)
    monkeypatch.setattr(ingest_upload_mod, "dedup_scan", fake_dedup)

    await fan_out_processing(
        application_ids=[uuid.uuid4()], upload_id=uuid.uuid4(), cycle_id=uuid.uuid4()
    )

    assert calls == []
