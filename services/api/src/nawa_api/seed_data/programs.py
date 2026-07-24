from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.journey.create_milestone_db import create_milestone_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.utils import days_ago
from nawa_api.seed_data.iam import IamSeedResult

SOS_RUBRIC_CRITERIA = [
    {
        "key": "novelty",
        "label_ar": "الابتكار",
        "label_en": "Novelty",
        "weight": 0.3,
        "scale_max": 10,
        "guidance_ar": "مدى تفرد الفكرة مقارنة بالحلول القائمة",
        "guidance_en": "How novel the idea is relative to existing solutions",
    },
    {
        "key": "feasibility",
        "label_ar": "الجدوى",
        "label_en": "Feasibility",
        "weight": 0.25,
        "scale_max": 10,
        "guidance_ar": "إمكانية تنفيذ الفكرة تقنيًا",
        "guidance_en": "Technical feasibility of the proposed solution",
    },
    {
        "key": "capability",
        "label_ar": "قدرة المتقدم",
        "label_en": "Applicant Capability",
        "weight": 0.25,
        "scale_max": 10,
        "guidance_ar": "خبرة ومهارة الفريق المتقدم",
        "guidance_en": "Team's demonstrated skill and experience",
    },
    {
        "key": "regional_impact",
        "label_ar": "الأثر الإقليمي",
        "label_en": "Regional Impact",
        "weight": 0.2,
        "scale_max": 10,
        "guidance_ar": "مدى تأثير الفكرة على المنطقة",
        "guidance_en": "Potential impact on the region",
    },
]


@dataclass
class ProgramsSeedResult:
    program_ids: dict[str, uuid.UUID] = field(default_factory=dict)
    cycle_ids: dict[str, uuid.UUID] = field(default_factory=dict)
    cohort_ids: dict[str, uuid.UUID] = field(default_factory=dict)
    sos_rubric_id: uuid.UUID | None = None
    velocity_milestone_template_ids: list[uuid.UUID] = field(default_factory=list)
    incubation_milestone_template_ids: list[uuid.UUID] = field(default_factory=list)


async def seed_programs(session: AsyncSession, *, iam: IamSeedResult) -> ProgramsSeedResult:
    result = ProgramsSeedResult()

    sos = await create_program_db(
        slug="innovation-fellowship",
        kind="competition",
        name_ar="نجوم العلوم",
        name_en="Innovation Fellowship",
        config={
            "intake": {"window_days": 60, "languages": ["ar", "en", "fr"]},
            "kpi_keys": ["mrr", "active_users", "runway_months", "team_size", "churn_pct"],
        },
        session=session,
    )
    velocity = await create_program_db(
        slug="velocity",
        kind="accelerator",
        name_ar="إكس إل آر 8",
        name_en="Velocity",
        config={"kpi_keys": ["mrr", "active_users", "runway_months", "team_size"]},
        session=session,
    )
    incubation = await create_program_db(
        slug="incubation-center",
        kind="incubation",
        name_ar="مركز الاحتضان",
        name_en="Incubation Center",
        config={"kpi_keys": ["mrr", "active_users", "runway_months", "team_size", "churn_pct"]},
        session=session,
    )
    r2s = await create_program_db(
        slug="research-to-startup",
        kind="research_translation",
        name_ar="من البحث إلى الشركة الناشئة",
        name_en="Research to Startup",
        session=session,
    )
    sir = await create_program_db(
        slug="startup-in-residence",
        kind="residency",
        name_ar="الشركة الناشئة المقيمة",
        name_en="Startup in Residence",
        session=session,
    )
    internship = await create_program_db(
        slug="internship-program",
        kind="internship",
        name_ar="برنامج التدريب",
        name_en="Internship Program",
        session=session,
    )

    for slug, program in [
        ("innovation-fellowship", sos),
        ("velocity", velocity),
        ("incubation-center", incubation),
        ("research-to-startup", r2s),
        ("startup-in-residence", sir),
        ("internship-program", internship),
    ]:
        result.program_ids[slug] = program.id

    rubric = await create_rubric_db(
        program_id=sos.id,
        version=1,
        criteria=SOS_RUBRIC_CRITERIA,
        name_ar="معيار التقييم - الموسم 18",
        name_en="Scoring Rubric v1",
        status="active",
        session=session,
    )
    result.sos_rubric_id = rubric.id

    # Cycles
    season_18 = await create_program_cycle_db(
        program_id=sos.id,
        slug="season-18",
        name_ar="الموسم 18",
        name_en="Season 18",
        status="screening",
        closes_at=days_ago(26),
        # 06-intake-copilot.md §6.2's "top-N-by-capacity" AI recommendation
        # band needs a real number to demo against — no capacity key is
        # specified anywhere in the spec pack, so this is a documented
        # choice, not a spec-literal value.
        config={"intake": {"shortlist_capacity": 20, "waitlist_capacity": 20}},
        session=session,
    )
    season_17 = await create_program_cycle_db(
        program_id=sos.id,
        slug="season-17",
        name_ar="الموسم 17",
        name_en="Season 17",
        status="completed",
        closes_at=days_ago(400),
        session=session,
    )
    cycle_14 = await create_program_cycle_db(
        program_id=velocity.id,
        slug="cycle-14",
        name_ar="الدورة 14",
        name_en="Cycle 14",
        status="completed",
        session=session,
    )
    cycle_15 = await create_program_cycle_db(
        program_id=velocity.id,
        slug="cycle-15",
        name_ar="الدورة 15",
        name_en="Cycle 15",
        status="draft",
        session=session,
    )
    incubation_cycle = await create_program_cycle_db(
        program_id=incubation.id,
        slug="incubation-2026",
        name_ar="دفعة 2026",
        name_en="2026 Cohort",
        status="active",
        session=session,
    )
    internship_cycle = await create_program_cycle_db(
        program_id=internship.id,
        slug="internship-2026",
        name_ar="تدريب 2026",
        name_en="2026 Internships",
        status="applications_open",
        session=session,
    )

    for slug, cycle in [
        ("sos-season-18", season_18),
        ("sos-season-17", season_17),
        ("velocity-cycle-14", cycle_14),
        ("velocity-cycle-15", cycle_15),
        ("incubation-2026", incubation_cycle),
        ("internship-2026", internship_cycle),
    ]:
        result.cycle_ids[slug] = cycle.id

    # Active cohorts: Velocity Cycle 14->15 handover + incubation.
    manager_user_id = iam.user_id("manager@nawa.local")
    velocity_cohort = await create_cohort_db(
        cycle_id=cycle_14.id,
        program_manager_user_id=manager_user_id,
        starts_at=days_ago(120),
        name_ar="دفعة الدورة 14",
        name_en="Cycle 14 Cohort",
        session=session,
    )
    incubation_cohort = await create_cohort_db(
        cycle_id=incubation_cycle.id,
        program_manager_user_id=manager_user_id,
        starts_at=days_ago(60),
        name_ar="دفعة الاحتضان 2026",
        name_en="Incubation 2026 Cohort",
        session=session,
    )
    result.cohort_ids["velocity-cycle-14"] = velocity_cohort.id
    result.cohort_ids["incubation-2026"] = incubation_cohort.id

    # Milestone templates + cohort-instantiated rows, spread across all five
    # progress states (including a few old-enough `blocked` rows for the
    # future stalled-milestone anomaly scan to find).
    velocity_titles = [
        ("Idea Validation", "التحقق من الفكرة"),
        ("Prototype v1", "النموذج الأولي 1"),
        ("Customer Discovery", "اكتشاف العملاء"),
        ("Pilot Launch", "إطلاق تجريبي"),
    ]
    for i, (title_en, title_ar) in enumerate(velocity_titles, start=1):
        template = await create_milestone_db(
            program_id=velocity.id,
            sequence=i,
            scope="template",
            title_ar=title_ar,
            title_en=title_en,
            due_offset_days=i * 21,
            session=session,
        )
        result.velocity_milestone_template_ids.append(template.id)
        instantiated = await create_milestone_db(
            program_id=velocity.id,
            sequence=i,
            scope="cohort",
            cohort_id=velocity_cohort.id,
            template_id=template.id,
            title_ar=title_ar,
            title_en=title_en,
            due_date=date.today(),
            session=session,
        )
        result.cohort_ids[f"velocity-milestone-{i}"] = instantiated.id

    incubation_titles = [
        ("First Revenue", "أول إيراد"),
        ("Team Hire", "توظيف الفريق"),
        ("Series Readiness", "الجاهزية لجولة تمويل"),
    ]
    for i, (title_en, title_ar) in enumerate(incubation_titles, start=1):
        template = await create_milestone_db(
            program_id=incubation.id,
            sequence=i,
            scope="template",
            title_ar=title_ar,
            title_en=title_en,
            due_offset_days=i * 30,
            session=session,
        )
        result.incubation_milestone_template_ids.append(template.id)
        instantiated = await create_milestone_db(
            program_id=incubation.id,
            sequence=i,
            scope="cohort",
            cohort_id=incubation_cohort.id,
            template_id=template.id,
            title_ar=title_ar,
            title_en=title_en,
            due_date=date.today(),
            session=session,
        )
        result.cohort_ids[f"incubation-milestone-{i}"] = instantiated.id

    return result
