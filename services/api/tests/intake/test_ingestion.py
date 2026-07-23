import io
import json
import uuid

import openpyxl
import pytest
import pytest_asyncio

from nawa_api.contracts.errors import ERR_INVALID_FIELDS, ApiError
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.services.intake.create_application import create_application
from nawa_api.services.intake.parse_upload import ParsedApplication, parse_upload

_MAP = {
    "Name": "applicant_name",
    "Email": "applicant_email",
    "Phone": "phone",
    "Idea": "q_idea",  # question column → original_answers
}


def test_parse_csv_with_mapping_and_raw_extra():
    csv_bytes = b"Name,Email,Phone,Idea,Weird\nAmina,a@x.io,+974123,We build,keepme\n"
    rows = parse_upload(csv_bytes, "batch.csv", _MAP)
    assert len(rows) == 1
    row = rows[0]
    assert row.applicant_name == "Amina"
    assert row.applicant_email == "a@x.io"
    assert row.phone == "+974123"
    assert row.original_answers == {"q_idea": "We build"}
    assert row.raw_extra == {"Weird": "keepme"}  # unmapped column preserved


def test_parse_json_array():
    data = [{"Name": "Zaid", "Email": "z@x.io", "Idea": "sensors"}]
    rows = parse_upload(json.dumps(data).encode(), "b.json", _MAP)
    assert rows[0].applicant_name == "Zaid"
    assert rows[0].original_answers == {"q_idea": "sensors"}


def test_parse_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "Email", "Idea"])
    ws.append(["Sara", "s@x.io", "robotics"])
    buf = io.BytesIO()
    wb.save(buf)
    rows = parse_upload(buf.getvalue(), "b.xlsx", _MAP)
    assert rows[0].applicant_name == "Sara"
    assert rows[0].original_answers == {"q_idea": "robotics"}


def test_unsupported_extension_is_400():
    with pytest.raises(ApiError) as exc:
        parse_upload(b"x", "b.txt", _MAP)
    assert exc.value is ERR_INVALID_FIELDS


def test_row_missing_required_fields_is_400():
    csv_bytes = b"Name,Idea\nAmina,we build\n"  # no Email column mapped
    with pytest.raises(ApiError) as exc:
        parse_upload(csv_bytes, "b.csv", _MAP)
    assert exc.value is ERR_INVALID_FIELDS


def test_json_not_a_list_is_400():
    with pytest.raises(ApiError):
        parse_upload(b'{"not": "a list"}', "b.json", _MAP)


# --- create service --------------------------------------------------------


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def test_create_application_persists_and_folds_phone_country(bound):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", name_en="P", kind="competition", session=bound
    )
    cycle = await create_program_cycle_db(
        program_id=program.id,
        slug=f"c-{uuid.uuid4().hex[:8]}",
        name_en="C",
        status="screening",
        session=bound,
    )
    await bound.commit()

    parsed = ParsedApplication(
        applicant_name="Amina",
        applicant_email="a@x.io",
        phone="+974123",
        country="QA",
        original_answers={"q_idea": "we build"},
        raw_extra={"note": "vip"},
    )
    dto = await create_application(cycle_id=cycle.id, parsed=parsed)
    assert dto["applicant_name"] == "Amina"
    assert dto["status"] == "submitted"
    assert dto["source_language"] == "en"  # interim until the normalize job runs

    # Minimal application (no phone/country) — exercises the skip branches.
    bare = ParsedApplication(applicant_name="Zaid", applicant_email="z@x.io")
    bare_dto = await create_application(cycle_id=cycle.id, parsed=bare)
    assert bare_dto["applicant_name"] == "Zaid"


async def test_create_application_raises_when_db_fails(monkeypatch):
    import nawa_api.services.intake.create_application as mod

    async def fake_db(**kwargs):
        return None

    monkeypatch.setattr(mod, "create_application_db", fake_db)
    with pytest.raises(ApiError) as exc:
        await create_application(
            cycle_id=uuid.uuid4(),
            parsed=ParsedApplication(applicant_name="X", applicant_email="x@x.io"),
        )
    assert exc.value is ERR_INVALID_FIELDS
