import uuid

import pytest
from sqlalchemy import select

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.models.identity import AuditLog
from nawa_api.utils.password import hash_password


async def _admin_bearer(client, email="eligadmin@example.com"):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Eligibility Admin",
    )
    group = await get_group_by_name_db(name="Administrators")
    await add_group_member_db(group_id=group.id, user_id=user.id)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "elig-dev"},
    )
    return {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


async def _application():
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P"
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C"
    )
    return await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Amina Al-Sayed",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
    )


@pytest.mark.asyncio
async def test_records_eligibility_proof_in_audit_log(client):
    headers = await _admin_bearer(client)
    app = await _application()

    resp = await client.post(
        f"/api/v1/intake/applications/{app.id}/eligibility-proof",
        headers=headers,
        json={
            "contract_address": "460870b0deadbeef",
            "tx_id": "005aa3a8cafef00d",
            "verdict": "eligible",
            "network": "preview",
            "min_age": 18,
            "max_prior_funding": 100000,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["proof_ref"] == "460870b0deadbeef@005aa3a8cafef00d"
    assert data["verdict"] == "eligible"

    # The proof reference must land in the immutable audit log.
    from nawa_api.db.utils import session_factory

    async with session_factory() as s:
        rows = (
            await s.execute(
                select(AuditLog).where(
                    AuditLog.action == "intake.eligibility.proof",
                    AuditLog.target_id == app.id,
                )
            )
        ).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.target_type == "intake_application"
    body = row.audit_metadata["body"]
    assert body["proof_ref"] == "460870b0deadbeef@005aa3a8cafef00d"
    assert body["verdict"] == "eligible"
    assert body["criteria"] == {"min_age": 18, "max_prior_funding": 100000}


@pytest.mark.asyncio
async def test_unknown_application_is_404(client):
    headers = await _admin_bearer(client)
    resp = await client.post(
        f"/api/v1/intake/applications/{uuid.uuid4()}/eligibility-proof",
        headers=headers,
        json={"contract_address": "a", "tx_id": "b", "verdict": "eligible"},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_bad_verdict_is_400(client):
    headers = await _admin_bearer(client)
    app = await _application()
    resp = await client.post(
        f"/api/v1/intake/applications/{app.id}/eligibility-proof",
        headers=headers,
        json={"contract_address": "a", "tx_id": "b", "verdict": "maybe"},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_requires_authentication(client):
    resp = await client.post(
        f"/api/v1/intake/applications/{uuid.uuid4()}/eligibility-proof",
        json={"contract_address": "a", "tx_id": "b", "verdict": "eligible"},
    )
    assert resp.status_code in (401, 403), resp.text
