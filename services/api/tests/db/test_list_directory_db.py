"""list_directory_db (08-community-hub.md §3, scoped to the directory read
only): visibility gating, text search over search_tsv, each filter, the
program_id derived-history filter, and pagination."""

import pytest

from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.community.list_directory_db import list_directory_db
from tests.db.factories import make_cohort, make_cycle, make_profile, make_program, make_user


@pytest.mark.asyncio
async def test_hides_private_and_inactive_owner_profiles(db_session):
    owner_ok = await make_user(db_session, email="ok@example.com", username="ok")
    profile_ok = await make_profile(db_session, user_id=owner_ok.id, handle="ok-founder")

    owner_private = await make_user(db_session, email="priv@example.com", username="priv")
    profile_private = await make_profile(
        db_session, user_id=owner_private.id, handle="priv-founder"
    )
    profile_private.is_public = False
    await db_session.flush()

    owner_inactive = await make_user(db_session, email="inactive@example.com", username="inact")
    profile_inactive = await make_profile(
        db_session, user_id=owner_inactive.id, handle="inactive-founder"
    )
    owner_inactive.is_active = False
    await db_session.flush()

    rows = await list_directory_db(session=db_session)
    ids = {r.id for r in rows}
    assert profile_ok.id in ids
    assert profile_private.id not in ids
    assert profile_inactive.id not in ids


@pytest.mark.asyncio
async def test_arabic_token_search_hits_the_arabic_fixture(db_session):
    owner_ar = await make_user(db_session, email="ar@example.com", username="ar")
    profile_ar = await make_profile(db_session, user_id=owner_ar.id, handle="ar-founder")
    profile_ar.venture_name_ar = "منصة الزراعة الذكية"
    await db_session.flush()

    owner_en = await make_user(db_session, email="en@example.com", username="en")
    profile_en = await make_profile(db_session, user_id=owner_en.id, handle="en-founder")
    profile_en.venture_name_en = "Smart Farming Platform"
    await db_session.flush()

    ar_rows = await list_directory_db(q="الزراعة", session=db_session)
    assert [r.id for r in ar_rows] == [profile_ar.id]

    en_rows = await list_directory_db(q="Farming", session=db_session)
    assert [r.id for r in en_rows] == [profile_en.id]


@pytest.mark.asyncio
async def test_domains_filter_is_array_overlap(db_session):
    owner_a = await make_user(db_session, email="a@example.com", username="a")
    profile_a = await make_profile(db_session, user_id=owner_a.id, handle="a-founder")
    profile_a.domains = ["agtech", "fintech"]
    owner_b = await make_user(db_session, email="b@example.com", username="b")
    profile_b = await make_profile(db_session, user_id=owner_b.id, handle="b-founder")
    profile_b.domains = ["edtech"]
    await db_session.flush()

    rows = await list_directory_db(domains=["agtech"], session=db_session)
    assert [r.id for r in rows] == [profile_a.id]


@pytest.mark.asyncio
async def test_skills_filter_is_array_overlap(db_session):
    owner_a = await make_user(db_session, email="a@example.com", username="a")
    profile_a = await make_profile(db_session, user_id=owner_a.id, handle="a-founder")
    profile_a.skills = ["cad", "hardware"]
    owner_b = await make_user(db_session, email="b@example.com", username="b")
    profile_b = await make_profile(db_session, user_id=owner_b.id, handle="b-founder")
    profile_b.skills = ["marketing"]
    await db_session.flush()

    rows = await list_directory_db(skills=["cad"], session=db_session)
    assert [r.id for r in rows] == [profile_a.id]


@pytest.mark.asyncio
async def test_sector_country_stage_equality_filters(db_session):
    owner_a = await make_user(db_session, email="a@example.com", username="a")
    profile_a = await make_profile(db_session, user_id=owner_a.id, handle="a-founder")
    profile_a.sector = "agtech"
    profile_a.country = "QA"
    profile_a.stage = "pilot"
    owner_b = await make_user(db_session, email="b@example.com", username="b")
    profile_b = await make_profile(db_session, user_id=owner_b.id, handle="b-founder")
    profile_b.sector = "fintech"
    profile_b.country = "AE"
    profile_b.stage = "idea"
    await db_session.flush()

    assert [r.id for r in await list_directory_db(sector="agtech", session=db_session)] == [
        profile_a.id
    ]
    assert [r.id for r in await list_directory_db(country="QA", session=db_session)] == [
        profile_a.id
    ]
    assert [r.id for r in await list_directory_db(stage="pilot", session=db_session)] == [
        profile_a.id
    ]


@pytest.mark.asyncio
async def test_mentors_filter(db_session):
    owner_a = await make_user(db_session, email="a@example.com", username="a")
    profile_a = await make_profile(db_session, user_id=owner_a.id, handle="a-founder")
    profile_a.is_mentor_eligible = True
    owner_b = await make_user(db_session, email="b@example.com", username="b")
    await make_profile(db_session, user_id=owner_b.id, handle="b-founder")
    await db_session.flush()

    rows = await list_directory_db(mentors=True, session=db_session)
    assert [r.id for r in rows] == [profile_a.id]

    # absent/false never filters
    rows_all = await list_directory_db(session=db_session)
    assert len(rows_all) == 2


@pytest.mark.asyncio
async def test_program_id_filter_via_derived_history(db_session):
    owner_a = await make_user(db_session, email="a@example.com", username="a")
    profile_a = await make_profile(db_session, user_id=owner_a.id, handle="a-founder")
    owner_b = await make_user(db_session, email="b@example.com", username="b")
    profile_b = await make_profile(db_session, user_id=owner_b.id, handle="b-founder")
    await db_session.flush()

    program = await make_program(db_session, slug="sos-directory")
    cycle = await make_cycle(db_session, program_id=program.id, slug="cyc-directory")
    manager = await make_user(db_session, email="mgr@example.com", username="mgr")
    cohort = await make_cohort(db_session, cycle_id=cycle.id, manager_user_id=manager.id)
    await create_cohort_member_db(cohort_id=cohort.id, profile_id=profile_a.id, session=db_session)

    rows = await list_directory_db(program_id=program.id, session=db_session)
    assert [r.id for r in rows] == [profile_a.id]
    assert profile_b.id not in {r.id for r in rows}


@pytest.mark.asyncio
async def test_pagination_limit_and_offset(db_session):
    for i in range(5):
        owner = await make_user(db_session, email=f"p{i}@example.com", username=f"p{i}")
        await make_profile(db_session, user_id=owner.id, handle=f"founder-{i}")
    await db_session.flush()

    page1 = await list_directory_db(limit=2, offset=0, session=db_session)
    page2 = await list_directory_db(limit=2, offset=2, session=db_session)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {r.id for r in page1}.isdisjoint({r.id for r in page2})


@pytest.mark.asyncio
async def test_combined_filters(db_session):
    owner_match = await make_user(db_session, email="match@example.com", username="match")
    profile_match = await make_profile(db_session, user_id=owner_match.id, handle="match-founder")
    profile_match.sector = "agtech"
    profile_match.domains = ["agtech"]
    profile_match.is_mentor_eligible = True

    owner_other = await make_user(db_session, email="other@example.com", username="other")
    profile_other = await make_profile(db_session, user_id=owner_other.id, handle="other-founder")
    profile_other.sector = "agtech"
    profile_other.domains = ["agtech"]
    profile_other.is_mentor_eligible = False
    await db_session.flush()

    rows = await list_directory_db(
        sector="agtech", domains=["agtech"], mentors=True, session=db_session
    )
    assert [r.id for r in rows] == [profile_match.id]
    assert profile_other.id not in {r.id for r in rows}
