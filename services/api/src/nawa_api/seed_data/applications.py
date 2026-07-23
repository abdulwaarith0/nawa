from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_application_embedding_db import create_application_embedding_db
from nawa_api.db.intake.create_dedup_match_db import create_dedup_match_db
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.utils import days_ago
from nawa_api.seed_data.embeddings import (
    EMBEDDING_MODEL,
    deterministic_vector,
    near_duplicate_vector,
    source_hash,
)
from nawa_api.seed_data.programs import ProgramsSeedResult
from nawa_api.seed_data.taxonomy import (
    ALL_COUNTRIES,
    FR_TEMPLATE,
    HIDDEN_GEM_AR_TEMPLATES,
    HIDDEN_GEM_EN_TEMPLATES,
    PERSONAS,
    STANDARD_AR_TEMPLATE,
    STANDARD_EN_TEMPLATE,
    TECH_DOMAINS_AR,
    TECH_DOMAINS_EN,
)

_RNG_SEED = 20260722
_SEASON_18_COUNT = 200
_SEASON_17_COUNT = 20
_HIDDEN_GEM_COUNT = 9
_CROSS_SEASON_DUP_PAIRS = 7
_INTRA_SEASON_DUP_PAIRS = 2


@dataclass
class ApplicationsSeedResult:
    hidden_gem_ids: list[uuid.UUID] = field(default_factory=list)
    dedup_pairs: list[tuple[uuid.UUID, uuid.UUID]] = field(default_factory=list)
    season_18_ids: list[uuid.UUID] = field(default_factory=list)
    season_17_ids: list[uuid.UUID] = field(default_factory=list)


def _random_names(rng: random.Random, count: int) -> list[str]:
    first_ar = ["أحمد", "فاطمة", "محمد", "ليلى", "يوسف", "مريم", "خالد", "سارة", "عمر", "هدى"]
    first_en = ["Ahmed", "Fatima", "Mohammed", "Layla", "Youssef", "Mariam", "Khalid", "Sara"]
    last = ["Al-Sayed", "Al-Nasser", "Boudiaf", "Chraibi", "Haddad", "Trabelsi", "Al-Kaabi"]
    names = []
    for i in range(count):
        pool = first_ar if i % 2 == 0 else first_en
        names.append(f"{rng.choice(pool)} {rng.choice(last)}")
    return names


def _build_answers(
    rng: random.Random,
    *,
    language: str,
    domain_en: str,
    domain_ar: str,
    persona_en: str,
    country: str,
    hidden_gem: bool,
) -> dict:
    if language == "fr":
        text = FR_TEMPLATE.format(domain=domain_en, persona=persona_en, country=country)
    elif language == "ar":
        if hidden_gem:
            text = rng.choice(HIDDEN_GEM_AR_TEMPLATES).format(domain=domain_ar)
        else:
            text = STANDARD_AR_TEMPLATE.format(
                domain=domain_ar, persona=persona_en, country=country
            )
    else:
        if hidden_gem:
            text = rng.choice(HIDDEN_GEM_EN_TEMPLATES).format(domain=domain_en)
        else:
            text = STANDARD_EN_TEMPLATE.format(
                domain=domain_en, persona=persona_en, country=country
            )
    return {"q1_problem": text, "q2_team": persona_en, "q3_country": country}


async def _create_one_application(
    session: AsyncSession,
    rng: random.Random,
    *,
    cycle_id: uuid.UUID,
    index: int,
    hidden_gem: bool = False,
) -> tuple:
    lang_roll = rng.random()
    language = "ar" if lang_roll < 0.55 else ("en" if lang_roll < 0.90 else "fr")
    domain_en, sector = rng.choice(TECH_DOMAINS_EN)
    domain_ar, _ = rng.choice(TECH_DOMAINS_AR)
    persona_en, _persona_ar = rng.choice(PERSONAS)
    country = rng.choice(ALL_COUNTRIES)
    name = _random_names(rng, 1)[0]
    email = f"applicant{index}@example.com"

    answers = _build_answers(
        rng,
        language=language,
        domain_en=domain_en,
        domain_ar=domain_ar,
        persona_en=persona_en,
        country=country,
        hidden_gem=hidden_gem,
    )
    application = await create_application_db(
        cycle_id=cycle_id,
        applicant_name=name,
        applicant_email=email,
        source_language=language,
        original_answers=answers,
        submitted_at=days_ago(rng.randint(1, 60)),
        session=session,
    )

    content_key = f"application-{application.id}"
    vector = deterministic_vector(content_key)
    await create_application_embedding_db(
        application_id=application.id,
        embedding=vector,
        embedding_model=EMBEDDING_MODEL,
        source_hash=source_hash(content_key),
        session=session,
    )
    return application, vector, sector


async def seed_applications(
    session: AsyncSession, *, programs: ProgramsSeedResult
) -> ApplicationsSeedResult:
    rng = random.Random(_RNG_SEED)
    result = ApplicationsSeedResult()

    season_18_id = programs.cycle_ids["sos-season-18"]
    season_17_id = programs.cycle_ids["sos-season-17"]

    hidden_gem_indices = set(rng.sample(range(_SEASON_18_COUNT), _HIDDEN_GEM_COUNT))

    season_18_apps: list[tuple] = []
    for i in range(_SEASON_18_COUNT):
        app, vector, _sector = await _create_one_application(
            session, rng, cycle_id=season_18_id, index=i, hidden_gem=i in hidden_gem_indices
        )
        season_18_apps.append((app, vector))
        result.season_18_ids.append(app.id)
        if i in hidden_gem_indices:
            result.hidden_gem_ids.append(app.id)

    season_17_apps: list[tuple] = []
    for i in range(_SEASON_17_COUNT):
        app, vector, _sector = await _create_one_application(
            session, rng, cycle_id=season_17_id, index=1000 + i
        )
        season_17_apps.append((app, vector))
        result.season_17_ids.append(app.id)

        # Season-17 rows are historical/decided with human scorecards.
        scorecard = await create_scorecard_db(
            application_id=app.id,
            rubric_id=programs.sos_rubric_id,
            rubric_version=1,
            prompt_version="seed-v0",
            source="human",
            total_score=round(rng.uniform(40, 95), 1),
            rationale_en="Reviewed by jury panel, Season 17.",
            status="final",
            session=session,
        )
        await create_scorecard_criterion_db(
            scorecard_id=scorecard.id,
            criterion_key="novelty",
            score=round(rng.uniform(4, 10), 1),
            weight=0.3,
            rationale_en="Jury-assessed novelty.",
            citations=[{"source": "answer:q1_problem", "quote": "reviewed"}],
            session=session,
        )

    # Cross-season duplicate pairs: same idea resubmitted, reworded, S17->S18.
    dedup_source = rng.sample(season_17_apps, min(_CROSS_SEASON_DUP_PAIRS, len(season_17_apps)))
    dedup_targets = rng.sample(season_18_apps, min(_CROSS_SEASON_DUP_PAIRS, len(season_18_apps)))
    for (orig_app, orig_vec), (dup_app, _) in zip(dedup_source, dedup_targets, strict=False):
        planted_vector = near_duplicate_vector(orig_vec, noise_key=f"dup-{dup_app.id}")
        await create_application_embedding_db(
            application_id=dup_app.id,
            embedding=planted_vector,
            embedding_model=EMBEDDING_MODEL,
            source_hash=source_hash(f"planted-dup-{dup_app.id}"),
            session=session,
        )
        similarity = 0.9
        await create_dedup_match_db(
            application_id=dup_app.id,
            matched_application_id=orig_app.id,
            similarity=similarity,
            session=session,
        )
        result.dedup_pairs.append((dup_app.id, orig_app.id))

    # Intra-season near-duplicates within Season 18.
    intra_pairs = rng.sample(season_18_apps, min(_INTRA_SEASON_DUP_PAIRS * 2, len(season_18_apps)))
    for j in range(0, len(intra_pairs) - 1, 2):
        (app_a, vec_a), (app_b, _) = intra_pairs[j], intra_pairs[j + 1]
        planted_vector = near_duplicate_vector(vec_a, noise_key=f"intra-dup-{app_b.id}")
        await create_application_embedding_db(
            application_id=app_b.id,
            embedding=planted_vector,
            embedding_model=EMBEDDING_MODEL,
            source_hash=source_hash(f"planted-intra-dup-{app_b.id}"),
            session=session,
        )
        await create_dedup_match_db(
            application_id=app_b.id,
            matched_application_id=app_a.id,
            similarity=0.9,
            session=session,
        )
        result.dedup_pairs.append((app_b.id, app_a.id))

    return result
