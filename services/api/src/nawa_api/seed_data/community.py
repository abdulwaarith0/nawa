from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.community.create_mentorship_db import create_mentorship_db
from nawa_api.db.community.create_opportunity_db import create_opportunity_db
from nawa_api.db.community.create_opportunity_match_db import create_opportunity_match_db
from nawa_api.db.community.create_request_db import create_request_db
from nawa_api.db.community.create_request_match_db import create_request_match_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db.utils import days_ago
from nawa_api.seed_data.profiles import ProfilesSeedResult
from nawa_api.seed_data.taxonomy import SKILLS

_RNG_SEED = 20260722

_REQUEST_TITLES_EN = [
    "Need a mechanical engineer for 2 weeks",
    "Seeking a pilot customer in health tech",
    "Looking for Arabic UX review",
    "Need help with regulatory approval",
    "Seeking a co-founder with data science background",
]
_OPPORTUNITY_TITLES_EN = [
    "Summer internship at program-based startup",
    "Grant: early-stage water-tech ventures",
    "Pilot program: agri-tech in the Gulf",
    "Speaking slot: demo day",
]


async def seed_community_data(session: AsyncSession, *, profiles: ProfilesSeedResult) -> None:
    rng = random.Random(_RNG_SEED + 3)
    profile_ids = profiles.profile_ids

    requests = []
    for i in range(25):
        owner = rng.choice(profile_ids)
        status = "closed" if i % 8 == 0 else ("matched" if i % 5 == 0 else "open")
        request = await create_request_db(
            profile_id=owner,
            kind=rng.choice(["talent", "pilot", "review", "intro", "funding"]),
            title_en=rng.choice(_REQUEST_TITLES_EN),
            skills_needed=rng.sample(SKILLS, k=2),
            duration_label=f"{rng.randint(1, 8)} weeks",
            status=status,
            session=session,
        )
        requests.append(request)

    match_count = 0
    for request in requests:
        for _ in range(rng.randint(1, 2)):
            if match_count >= 40:
                break
            candidate = rng.choice(profile_ids)
            await create_request_match_db(
                request_id=request.id,
                profile_id=candidate,
                score=round(rng.uniform(0.4, 0.95), 2),
                rationale_en="Skills overlap with the request's stated needs.",
                matched_skills=rng.sample(SKILLS, k=1),
                status=rng.choice(["suggested", "notified"]),
                session=session,
            )
            match_count += 1

    staff = await create_user_db(
        email="opportunities-poster@example.com",
        username="oppposter",
        password_hash="$2b$04$" + "a" * 53,
        full_name="Opportunities Poster",
        session=session,
    )
    opportunities = []
    for i in range(15):
        deadline = days_ago(-rng.randint(3, 90))  # future deadline
        status = "closed" if i % 7 == 0 else "open"
        opp = await create_opportunity_db(
            posted_by_user_id=staff.id,
            kind=rng.choice(["internship", "job", "grant", "pilot", "speaking"]),
            title_en=rng.choice(_OPPORTUNITY_TITLES_EN),
            org_name="Partner Co.",
            tags=["program"],
            skills=rng.sample(SKILLS, k=2),
            deadline_at=deadline,
            status=status,
            session=session,
        )
        opportunities.append(opp)

    for opp in opportunities[:20]:
        candidate = rng.choice(profile_ids)
        await create_opportunity_match_db(
            opportunity_id=opp.id,
            profile_id=candidate,
            score=round(rng.uniform(0.4, 0.95), 2),
            status=rng.choice(["suggested", "notified", "interested"]),
            session=session,
        )

    for _ in range(12):
        mentor, mentee = rng.sample(profile_ids, 2)
        await create_mentorship_db(
            mentor_profile_id=mentor,
            mentee_profile_id=mentee,
            matched_by="ai",
            score=round(rng.uniform(0.5, 0.9), 2),
            rationale_en="Shared sector experience and complementary skills.",
            status=rng.choice(["suggested", "active", "completed"]),
            session=session,
        )
