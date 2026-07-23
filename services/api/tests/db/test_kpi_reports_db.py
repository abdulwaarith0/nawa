from datetime import UTC, date, datetime, timedelta

import pytest

from nawa_api.db.kpi.create_kpi_definition_db import create_kpi_definition_db
from nawa_api.db.kpi.create_kpi_entry_db import create_kpi_entry_db
from nawa_api.db.kpi.list_kpi_definitions_db import list_kpi_definitions_db
from nawa_api.db.kpi.list_kpi_series_db import list_kpi_series_db
from nawa_api.db.kpi.refresh_kpi_snapshot_db import refresh_kpi_snapshot_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.profiles.get_profile_by_id_any_status_db import get_profile_by_id_any_status_db
from nawa_api.db.reports.create_anomaly_db import create_anomaly_db
from nawa_api.db.reports.create_check_in_db import create_check_in_db
from nawa_api.db.reports.create_report_db import create_report_db
from nawa_api.db.users.create_user_db import create_user_db


async def _make_profile(db_session, *, email: str, handle: str):
    user = await create_user_db(
        email=email,
        username=handle,
        password_hash="hashed",
        full_name=handle,
        session=db_session,
    )
    return await create_founder_profile_db(
        user_id=user.id, handle=handle, display_name_en=handle, session=db_session
    )


@pytest.mark.asyncio
async def test_kpi_definition_create_and_list(db_session):
    created = await create_kpi_definition_db(
        key="mrr-test", name_en="MRR", value_type="currency", session=db_session
    )
    assert created is not None
    rows = await list_kpi_definitions_db(session=db_session)
    assert any(d.key == "mrr-test" for d in rows)


@pytest.mark.asyncio
async def test_kpi_entry_series_and_snapshot_refresh(db_session):
    profile = await _make_profile(db_session, email="kpi@example.com", handle="kpi-founder")
    definition = await create_kpi_definition_db(
        key="mrr-kpi-test", name_en="MRR", value_type="currency", session=db_session
    )

    week1 = date.today() - timedelta(weeks=2)
    week2 = date.today() - timedelta(weeks=1)
    now = datetime.now(UTC)

    ok1 = await create_kpi_entry_db(
        profile_id=profile.id,
        kpi_definition_id=definition.id,
        period_start=week1,
        value=1000,
        confirmed_at=now,
        session=db_session,
    )
    ok2 = await create_kpi_entry_db(
        profile_id=profile.id,
        kpi_definition_id=definition.id,
        period_start=week2,
        value=1200,
        confirmed_at=now,
        session=db_session,
    )
    assert ok1 and ok2

    series = await list_kpi_series_db(
        profile_id=profile.id, kpi_definition_id=definition.id, session=db_session
    )
    assert len(series) == 2
    assert series[0].period_start == week2  # newest first

    refreshed = await refresh_kpi_snapshot_db(profile_id=profile.id, session=db_session)
    assert refreshed is True

    updated_profile = await get_profile_by_id_any_status_db(
        profile_id=profile.id, session=db_session
    )
    snapshot = updated_profile.kpi_snapshot["mrr-kpi-test"]
    assert snapshot["value"] == 1200.0
    assert snapshot["delta_pct"] == pytest.approx(20.0)


@pytest.mark.asyncio
async def test_kpi_entry_upsert_corrects_existing_period(db_session):
    profile = await _make_profile(db_session, email="kpi2@example.com", handle="kpi-founder-2")
    definition = await create_kpi_definition_db(
        key="active-users-test", name_en="Active Users", session=db_session
    )
    period = date.today()
    now = datetime.now(UTC)
    await create_kpi_entry_db(
        profile_id=profile.id,
        kpi_definition_id=definition.id,
        period_start=period,
        value=10,
        confirmed_at=now,
        session=db_session,
    )
    await create_kpi_entry_db(
        profile_id=profile.id,
        kpi_definition_id=definition.id,
        period_start=period,
        value=15,
        confirmed_at=now,
        session=db_session,
    )
    series = await list_kpi_series_db(
        profile_id=profile.id, kpi_definition_id=definition.id, session=db_session
    )
    assert len(series) == 1
    assert float(series[0].value) == 15.0


@pytest.mark.asyncio
async def test_check_in_and_report_and_anomaly_creation(db_session):
    profile = await _make_profile(db_session, email="checkin@example.com", handle="checkin-founder")
    check_in = await create_check_in_db(
        profile_id=profile.id,
        period_start=date.today(),
        status="submitted",
        summary_en="Good progress this month.",
        session=db_session,
    )
    assert check_in is not None

    report = await create_report_db(
        kind="founder_monthly",
        subject_type="profile",
        subject_id=profile.id,
        period_start=date.today().replace(day=1),
        period_end=date.today(),
        content={"mrr": {"value": 1200, "source": {"table": "kpi_entries", "field": "value"}}},
        session=db_session,
    )
    assert report is not None

    created = await create_anomaly_db(
        profile_id=profile.id,
        kind="runway",
        severity="warning",
        window_start=date.today() - timedelta(weeks=4),
        window_end=date.today(),
        dedupe_key=f"{profile.id}:runway:-:{date.today()}",
        details={"runway_months": 3.5},
        session=db_session,
    )
    assert created is True

    # Re-scanning updates the open row instead of creating a duplicate.
    updated = await create_anomaly_db(
        profile_id=profile.id,
        kind="runway",
        severity="critical",
        window_start=date.today() - timedelta(weeks=4),
        window_end=date.today(),
        dedupe_key=f"{profile.id}:runway:-:{date.today()}",
        details={"runway_months": 2.0},
        session=db_session,
    )
    assert updated is True
