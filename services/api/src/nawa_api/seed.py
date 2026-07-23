"""The idempotent wipe-and-reseed demo dataset. Run as:

    uv run python -m nawa_api.seed

Safety: refuses to run against anything but nawa_dev / nawa_test_* (checked
before any connection opens, per runtime.db_guard's shared constant).
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url

import nawa_api  # noqa: F401  (Windows event-loop policy)
from nawa_api.db.utils import in_transaction
from nawa_api.models import Base
from nawa_api.runtime.db_guard import is_seed_safe_db_name
from nawa_api.runtime.postgres import engine
from nawa_api.runtime.settings import get_settings
from nawa_api.seed_data.applications import seed_applications
from nawa_api.seed_data.community import seed_community_data
from nawa_api.seed_data.iam import CREDENTIALS_TABLE, seed_iam
from nawa_api.seed_data.profiles import seed_profiles_and_kpis
from nawa_api.seed_data.programs import seed_programs
from nawa_api.seed_data.reports import seed_reports_and_ambience
from nawa_api.seed_data.resources import seed_resources
from nawa_api.seed_data.site_config import seed_site_config


def _assert_seed_safe() -> None:
    db_name = make_url(get_settings().database_url).database
    if not is_seed_safe_db_name(db_name):
        print(
            f"Refusing to seed database {db_name!r}: seeding wipes all data and only runs "
            f"against nawa_dev or nawa_test_* databases.",
            file=sys.stderr,
        )
        raise SystemExit(1)


async def _truncate_all() -> None:
    table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with engine.connect() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
        await conn.commit()


async def run_seed() -> None:
    _assert_seed_safe()
    await _truncate_all()

    # Each phase runs in its own transaction (in_transaction commits on exit)
    # so a later phase's data is visible to db-layer reads within it, and a
    # failure surfaces which phase broke rather than rolling back everything.
    async with in_transaction() as session:
        iam = await seed_iam(session)

    async with in_transaction() as session:
        programs = await seed_programs(session, iam=iam)

    async with in_transaction() as session:
        applications_result = await seed_applications(session, programs=programs)

    async with in_transaction() as session:
        profiles_result = await seed_profiles_and_kpis(session, programs=programs)

    async with in_transaction() as session:
        await seed_community_data(session, profiles=profiles_result)

    async with in_transaction() as session:
        await seed_resources(session)

    async with in_transaction() as session:
        await seed_reports_and_ambience(
            session,
            profiles=profiles_result,
            programs=programs,
            applications=applications_result,
            iam=iam,
        )

    ground_truth = {
        "hidden_gem_application_ids": [str(i) for i in applications_result.hidden_gem_ids],
        "dedup_pair_ids": [[str(a), str(b)] for a, b in applications_result.dedup_pairs],
        "anomaly_profile_ids": profiles_result.anomaly_profile_ids,
    }
    async with in_transaction() as session:
        await seed_site_config(session, ground_truth=ground_truth)

    print("\nSeed complete. Login credentials (password: `password` for all):\n")
    print(f"{'Identifier':<28} {'Group':<20} {'Password'}")
    for identifier, group in CREDENTIALS_TABLE:
        print(f"{identifier:<28} {group:<20} password")


def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
