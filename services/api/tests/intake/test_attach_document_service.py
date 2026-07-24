import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from nawa_api.contracts.errors import ERR_NOT_FOUND, ApiError
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.models.intake import ApplicationDocument
from nawa_api.runtime.redis import get_redis
from nawa_api.runtime.storage import get_storage_provider, reset_storage_provider_cache
from nawa_api.services.intake.attach_document import attach_document


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    reset_storage_provider_cache()
    yield db_session
    reset_storage_provider_cache()


async def _application(session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    return await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "an idea"},
        session=session,
    )


@pytest.mark.asyncio
async def test_attach_document_stores_content_and_persists_a_row(bound):
    app = await _application(bound)
    await bound.commit()

    result = await attach_document(
        application_id=app.id,
        filename="pitch.pdf",
        content=b"pdf bytes here",
        mime_type="application/pdf",
    )

    assert result["file_name"] == "pitch.pdf"
    assert result["kind"] == "attachment"
    assert result["size_bytes"] == len(b"pdf bytes here")

    row = (
        await bound.execute(
            select(ApplicationDocument).where(ApplicationDocument.application_id == app.id)
        )
    ).scalar_one()
    assert get_storage_provider().get_object(row.storage_key) == b"pdf bytes here"
    assert row.storage_key.startswith(f"intake/documents/{app.id}/")


@pytest.mark.asyncio
async def test_attach_document_defaults_invalid_kind_to_attachment(bound):
    app = await _application(bound)
    await bound.commit()

    result = await attach_document(
        application_id=app.id,
        filename="notes.txt",
        content=b"notes",
        mime_type="text/plain",
        kind="not-a-real-kind",
    )
    assert result["kind"] == "attachment"


@pytest.mark.asyncio
async def test_attach_document_missing_application_raises_not_found(bound):
    with pytest.raises(ApiError) as exc_info:
        await attach_document(
            application_id=uuid.uuid4(),
            filename="x.pdf",
            content=b"x",
            mime_type="application/pdf",
        )
    assert exc_info.value == ERR_NOT_FOUND


@pytest.mark.asyncio
async def test_attach_document_invalidates_the_scorecard_cache(bound):
    app = await _application(bound)
    await bound.commit()

    key = f"services:intake:get_scorecard:{app.id}"
    await get_redis().set(key, "cached-value")

    await attach_document(
        application_id=app.id,
        filename="pitch.pdf",
        content=b"bytes",
        mime_type="application/pdf",
    )

    assert await get_redis().get(key) is None
