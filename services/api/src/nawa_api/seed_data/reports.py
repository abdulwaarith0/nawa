from __future__ import annotations

import random
import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.ai_calls.create_ai_call_db import create_ai_call_db
from nawa_api.db.audit.create_audit_log_db import create_audit_log_db
from nawa_api.db.journey.create_assistant_message_db import create_assistant_message_db
from nawa_api.db.journey.create_assistant_thread_db import create_assistant_thread_db
from nawa_api.db.journey.create_digest_db import create_digest_db
from nawa_api.db.notifications.create_notification_db import create_notification_db
from nawa_api.db.reports.create_anomaly_db import create_anomaly_db
from nawa_api.db.reports.create_report_db import create_report_db
from nawa_api.seed_data.applications import ApplicationsSeedResult
from nawa_api.seed_data.iam import IamSeedResult
from nawa_api.seed_data.profiles import ProfilesSeedResult
from nawa_api.seed_data.programs import ProgramsSeedResult

_RNG_SEED = 20260722

_ANOMALY_KIND_BY_PATTERN = {
    "runway_critical": "runway",
    "churn_spike": "churn_spike",
    "stalled": "growth_stall",
}


async def seed_reports_and_ambience(
    session: AsyncSession,
    *,
    profiles: ProfilesSeedResult,
    programs: ProgramsSeedResult,
    applications: ApplicationsSeedResult,
    iam: IamSeedResult,
) -> None:
    rng = random.Random(_RNG_SEED + 4)

    # Reports: 6 founder_monthly (mixed lifecycle) + 1 cycle_outcome for S17.
    statuses = ["draft", "review", "final", "draft", "review", "final"]
    for i, profile_id_str in enumerate(profiles.profile_ids[:6]):
        await create_report_db(
            kind="founder_monthly",
            subject_type="profile",
            subject_id=profile_id_str,
            period_start=date.today().replace(day=1) - timedelta(days=30),
            period_end=date.today(),
            content={
                "mrr": {
                    "value": 1500 + i * 100,
                    "source": {"table": "kpi_entries", "field": "value"},
                }
            },
            rendered_en="Monthly report narrative.",
            status=statuses[i],
            generated_by="ai",
            session=session,
        )
    await create_report_db(
        kind="cycle_outcome",
        subject_type="cycle",
        subject_id=programs.cycle_ids["sos-season-17"],
        period_start=date.today() - timedelta(days=400),
        period_end=date.today() - timedelta(days=340),
        content={
            "applicants": {
                "value": len(applications.season_17_ids),
                "source": {"table": "applications", "field": "count"},
            }
        },
        rendered_en="Season 17 cycle outcome report.",
        status="final",
        generated_by="ai",
        session=session,
    )

    # Anomalies consistent with the seeded KPI patterns (churn-spike + runway-critical => 10).
    for pattern in ("runway_critical", "churn_spike"):
        kind = _ANOMALY_KIND_BY_PATTERN[pattern]
        for profile_id_str in profiles.anomaly_profile_ids.get(pattern, []):
            profile_id = uuid.UUID(profile_id_str)
            await create_anomaly_db(
                profile_id=profile_id,
                kind=kind,
                severity="critical" if pattern == "runway_critical" else "warning",
                window_start=date.today() - timedelta(weeks=8),
                window_end=date.today(),
                dedupe_key=f"{profile_id}:{kind}:-:{date.today() - timedelta(weeks=8)}",
                details={"pattern": pattern},
                status=rng.choice(["open", "acknowledged"]),
                session=session,
            )

    # Ambience: notifications, digests, audit logs, ai_calls, assistant threads.
    for i in range(40):
        user_index = i % len(profiles.profile_ids)
        # Notifications reference users, not profiles directly; reuse the
        # admin account as a stand-in recipient pool member alongside seeded users.
        await create_notification_db(
            user_id=iam.user_id("member@nawa.local"),
            kind=rng.choice(["request.match", "opportunity.match", "digest.ready"]),
            title_en="You have a new update",
            body_en="Check your dashboard for details.",
            payload={"surface": "community", "id": str(profiles.profile_ids[user_index])},
            session=session,
        )

    for kind, scope_type, scope_id in [
        ("cohort", "cohort", programs.cohort_ids["velocity-cycle-14"]),
        ("cohort", "cohort", programs.cohort_ids["incubation-2026"]),
        ("program_manager", "cycle", programs.cycle_ids["sos-season-18"]),
    ]:
        await create_digest_db(
            kind=kind,
            scope_type=scope_type,
            scope_id=scope_id,
            period_start=date.today() - timedelta(days=7),
            period_end=date.today(),
            stats={"active_members": len(profiles.profile_ids)},
            content_en="Weekly digest summary.",
            generated_by="cron",
            status="sent",
            session=session,
        )

    for _ in range(30):
        await create_audit_log_db(
            actor_id=iam.user_id("manager@nawa.local"),
            action=rng.choice(["iam.policy.update", "application.override", "auth.login"]),
            target_type="application",
            target_id=rng.choice(applications.season_17_ids),
            status_code=200,
            duration_ms=rng.randint(5, 200),
            session=session,
        )

    for i in range(20):
        await create_ai_call_db(
            task="intake.score",
            provider="mock",
            model="mock-large",
            prompt_hash=f"seed-hash-{i}",
            prompt_version="seed-v0",
            status="ok",
            tokens_in=rng.randint(200, 800),
            tokens_out=rng.randint(100, 400),
            cost_estimate=round(rng.uniform(0.001, 0.02), 4),
            latency_ms=rng.randint(200, 2000),
            cycle_id=programs.cycle_ids["sos-season-17"],
            session=session,
        )

    for i in range(2):
        thread = await create_assistant_thread_db(
            user_id=iam.user_id("founder@nawa.local"),
            kind="assistant",
            language="ar" if i == 0 else "en",
            session=session,
        )
        await create_assistant_message_db(
            thread_id=thread.id,
            role="user",
            content="ما هي إمكانيات مختبر التصنيع؟" if i == 0 else "What lab capabilities exist?",
            language="ar" if i == 0 else "en",
            session=session,
        )
        answer_ar = "يوفر المختبر خدمات النمذجة السريعة."
        answer_en = "The fab lab offers rapid prototyping."
        await create_assistant_message_db(
            thread_id=thread.id,
            role="assistant",
            content=answer_ar if i == 0 else answer_en,
            language="ar" if i == 0 else "en",
            citations=[{"resource_chunk_id": "seed", "title": "Fab Lab Capabilities"}],
            confidence=0.8,
            intent="informational",
            session=session,
        )
