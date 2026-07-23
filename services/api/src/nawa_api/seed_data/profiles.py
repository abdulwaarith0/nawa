from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.kpi.create_kpi_definition_db import create_kpi_definition_db
from nawa_api.db.kpi.create_kpi_entry_db import create_kpi_entry_db
from nawa_api.db.kpi.refresh_kpi_snapshot_db import refresh_kpi_snapshot_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.profiles.set_profile_embedding_db import set_profile_embedding_db
from nawa_api.db.reports.create_check_in_db import create_check_in_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db.utils import weeks_ago
from nawa_api.seed_data.embeddings import EMBEDDING_MODEL, deterministic_vector
from nawa_api.seed_data.programs import ProgramsSeedResult
from nawa_api.seed_data.taxonomy import ALL_COUNTRIES, SECTORS, SKILLS

_RNG_SEED = 20260722
_PROFILE_COUNT = 50
_WEEKS = 26

_PATTERN_COUNTS = {
    "steady_growth": 30,
    "stalled": 10,
    "churn_spike": 6,
    "runway_critical": 4,
}


@dataclass
class ProfilesSeedResult:
    profile_ids: list[uuid.UUID] = field(default_factory=list)
    kpi_definition_ids: dict[str, uuid.UUID] = field(default_factory=dict)
    anomaly_profile_ids: dict[str, list[str]] = field(default_factory=dict)
    # profile_id -> cohort_member_id
    cohort_member_ids: dict[uuid.UUID, uuid.UUID] = field(default_factory=dict)


def _weekly_series(rng: random.Random, pattern: str) -> dict[str, list[float]]:
    """Returns {kpi_key: [value_week_0_oldest, ..., value_week_25_newest]}."""
    mrr, users, runway, team, churn = [], [], [], [], []
    base_mrr = rng.uniform(500, 3000)
    base_users = rng.uniform(50, 300)
    base_runway = rng.uniform(8, 14)
    base_team = rng.randint(2, 6)

    for w in range(_WEEKS):
        if pattern == "steady_growth":
            growth = 1.0 + 0.04 * w
            mrr.append(base_mrr * growth)
            users.append(base_users * growth)
            runway.append(max(base_runway - 0.02 * w, 6))
            churn.append(rng.uniform(2, 5))
        elif pattern == "stalled":
            plateau_start = _WEEKS - 8
            growth = 1.0 + 0.03 * min(w, plateau_start)
            mrr.append(base_mrr * growth)
            users.append(base_users * growth)
            runway.append(max(base_runway - 0.03 * w, 5))
            churn.append(rng.uniform(3, 6))
        elif pattern == "churn_spike":
            growth = 1.0 + 0.03 * w
            mrr.append(base_mrr * growth)
            users.append(base_users * growth)
            runway.append(max(base_runway - 0.03 * w, 5))
            spike_start = _WEEKS - 4
            churn.append(rng.uniform(3, 5) if w < spike_start else rng.uniform(15, 25))
        else:  # runway_critical
            growth = 1.0 + 0.01 * w
            mrr.append(base_mrr * growth * 0.6)
            users.append(base_users * growth * 0.6)
            decay_start = _WEEKS - 10
            if w < decay_start:
                runway.append(max(base_runway - 0.05 * w, 6))
            else:
                weeks_into_decay = w - decay_start
                runway.append(max(base_runway - 0.05 * decay_start - 0.5 * weeks_into_decay, 1.5))
            churn.append(rng.uniform(4, 8))
        team.append(base_team + (1 if w > _WEEKS // 2 else 0))

    return {
        "mrr": mrr,
        "active_users": users,
        "runway_months": runway,
        "team_size": [float(t) for t in team],
        "churn_pct": churn,
    }


async def _seed_kpi_definitions(session: AsyncSession, *, incubation_program_id: uuid.UUID) -> dict:
    ids: dict[str, uuid.UUID] = {}
    global_defs = [
        ("mrr", "MRR", "الإيراد الشهري المتكرر", "currency", "last"),
        ("active_users", "Active Users", "المستخدمون النشطون", "count", "last"),
        ("runway_months", "Runway (months)", "مدة الاستمرارية (أشهر)", "number", "last"),
        ("team_size", "Team Size", "حجم الفريق", "count", "last"),
        ("churn_pct", "Churn %", "نسبة التسرب", "percent", "avg"),
    ]
    for key, name_en, name_ar, value_type, aggregation in global_defs:
        row = await create_kpi_definition_db(
            key=key,
            name_en=name_en,
            name_ar=name_ar,
            value_type=value_type,
            aggregation=aggregation,
            session=session,
        )
        ids[key] = row.id

    program_defs = [
        ("pilot_customers", "Pilot Customers", "عملاء تجريبيون"),
        ("milestone_completion_pct", "Milestone Completion %", "نسبة إنجاز المعالم"),
    ]
    for key, name_en, name_ar in program_defs:
        row = await create_kpi_definition_db(
            key=key,
            name_en=name_en,
            name_ar=name_ar,
            program_id=incubation_program_id,
            session=session,
        )
        ids[key] = row.id
    return ids


async def seed_profiles_and_kpis(
    session: AsyncSession, *, programs: ProgramsSeedResult
) -> ProfilesSeedResult:
    rng = random.Random(_RNG_SEED + 1)
    result = ProfilesSeedResult()

    kpi_ids = await _seed_kpi_definitions(
        session, incubation_program_id=programs.program_ids["incubation-center"]
    )
    result.kpi_definition_ids = kpi_ids

    patterns: list[str] = []
    for pattern, count in _PATTERN_COUNTS.items():
        patterns.extend([pattern] * count)
    rng.shuffle(patterns)

    cohort_pool = [
        programs.cohort_ids["velocity-cycle-14"],
        programs.cohort_ids["incubation-2026"],
    ]
    # ~30 profiles distributed across cohorts, some in two (alumni).
    cohort_assignment_indices = set(rng.sample(range(_PROFILE_COUNT), 30))
    alumni_indices = set(rng.sample(sorted(cohort_assignment_indices), 6))

    now = datetime.now(UTC)

    for i in range(_PROFILE_COUNT):
        handle = f"founder-{i:03d}"
        sector = rng.choice(SECTORS)
        country = rng.choice(ALL_COUNTRIES)
        skills = rng.sample(SKILLS, k=rng.randint(2, 4))
        user = await create_user_db(
            email=f"founder{i:03d}@example.com",
            username=handle,
            # placeholder hash: these 50 seed accounts are never logged into
            password_hash="$2b$04$" + "a" * 53,
            full_name=f"Founder {i:03d}",
            session=session,
        )
        profile = await create_founder_profile_db(
            user_id=user.id,
            handle=handle,
            display_name_ar=f"مؤسس {i:03d}",
            display_name_en=f"Founder {i:03d}",
            venture_name_en=f"Venture {i:03d}",
            venture_summary_en=f"A {sector} startup based in {country}.",
            sector=sector,
            country=country,
            stage=rng.choice(["idea", "prototype", "pilot", "revenue", "growth"]),
            skills=skills,
            session=session,
        )
        result.profile_ids.append(profile.id)

        content_key = f"profile-{profile.id}"
        vector = deterministic_vector(content_key)
        await set_profile_embedding_db(
            profile_id=profile.id,
            embedding=vector,
            embedding_model=EMBEDDING_MODEL,
            session=session,
        )

        if i in cohort_assignment_indices:
            cohort_id = cohort_pool[i % len(cohort_pool)]
            member = await create_cohort_member_db(
                cohort_id=cohort_id, profile_id=profile.id, session=session
            )
            result.cohort_member_ids[profile.id] = member.id
            if i in alumni_indices:
                other_cohort = cohort_pool[(i + 1) % len(cohort_pool)]
                await create_cohort_member_db(
                    cohort_id=other_cohort, profile_id=profile.id, session=session
                )

        pattern = patterns[i]
        series = _weekly_series(rng, pattern)
        for w in range(_WEEKS):
            period = weeks_ago(_WEEKS - 1 - w)
            # A few profiles miss random weeks, in the steady-growth group only.
            if pattern == "steady_growth" and rng.random() < 0.04:
                continue
            for key in ("mrr", "active_users", "runway_months", "team_size", "churn_pct"):
                await create_kpi_entry_db(
                    profile_id=profile.id,
                    kpi_definition_id=kpi_ids[key],
                    period_start=period,
                    value=round(series[key][w], 2),
                    confirmed_at=now,
                    source="import",
                    session=session,
                )

        await refresh_kpi_snapshot_db(profile_id=profile.id, session=session)

        if pattern != "steady_growth":
            result.anomaly_profile_ids.setdefault(pattern, []).append(str(profile.id))

        if profile.id in result.cohort_member_ids:
            for w in range(12):
                period = weeks_ago(11 - w)
                missed = rng.random() < 0.1
                await create_check_in_db(
                    profile_id=profile.id,
                    period_start=period,
                    channel="conversational",
                    language="ar" if i % 2 == 0 else "en",
                    status="missed" if missed else "submitted",
                    transcript=(
                        []
                        if missed
                        else [
                            {"role": "assistant", "content": "كيف كان أداء مشروعك هذا الأسبوع؟"},
                            {"role": "user", "content": "الأداء جيد، الإيرادات في تحسن."},
                        ]
                    ),
                    summary_en=None if missed else "Steady progress reported.",
                    session=session,
                )

    return result
