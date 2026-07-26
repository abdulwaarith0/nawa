"""Cached, filterable directory read (08-community-hub.md §3.3).

Key services:community:list_directory:<canonical-param-hash>, TTL 300s.
The hash is fully deterministic: every filter participates, an absent
param hashes as "*", array params are sorted before hashing (order never
changes the cache key). Never caches an empty page.

Invalidation: any founder-profile write should bust
`services:community:list_directory:*` — `decide_application.py`'s accept
path already fires this exact glob (built ahead of this service existing,
per its own comment). No profile-write endpoint exists in this codebase yet
(out of scope for this slice cut), so there is no second call site to wire.
"""

from __future__ import annotations

import json
import uuid
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.db.community.list_directory_db import list_directory_db
from nawa_api.db.utils import clamp_pagination
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 300
_KEY_PREFIX = "services:community:list_directory"


class _DirectoryPage(BaseModel):
    items: list[dict]


def cache_key(
    *,
    q: str | None,
    domains: list[str] | None,
    skills: list[str] | None,
    sector: str | None,
    country: str | None,
    program_id: uuid.UUID | None,
    stage: str | None,
    mentors: bool | None,
    limit: int,
    offset: int,
) -> str:
    raw = json.dumps(
        {
            "q": q or "*",
            "domains": sorted(domains) if domains else "*",
            "skills": sorted(skills) if skills else "*",
            "sector": sector or "*",
            "country": country or "*",
            "program_id": str(program_id) if program_id else "*",
            "stage": stage or "*",
            "mentors": True if mentors else "*",
            "limit": limit,
            "offset": offset,
        },
        sort_keys=True,
    )
    return f"{_KEY_PREFIX}:{sha256(raw.encode()).hexdigest()[:24]}"


def _dto(profile) -> dict:
    return {
        "id": str(profile.id),
        "handle": profile.handle,
        "display_name_ar": profile.display_name_ar,
        "display_name_en": profile.display_name_en,
        "headline_ar": profile.headline_ar,
        "headline_en": profile.headline_en,
        "venture_name_ar": profile.venture_name_ar,
        "venture_name_en": profile.venture_name_en,
        "sector": profile.sector,
        "country": profile.country,
        "stage": profile.stage,
        "skills": profile.skills,
        "domains": profile.domains,
        "is_mentor_eligible": profile.is_mentor_eligible,
    }


async def list_directory(
    *,
    q: str | None = None,
    domains: list[str] | None = None,
    skills: list[str] | None = None,
    sector: str | None = None,
    country: str | None = None,
    program_id: uuid.UUID | None = None,
    stage: str | None = None,
    mentors: bool | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)

    key = cache_key(
        q=q,
        domains=domains,
        skills=skills,
        sector=sector,
        country=country,
        program_id=program_id,
        stage=stage,
        mentors=mentors,
        limit=clamped_limit,
        offset=clamped_offset,
    )
    cached = await redis_retrieve_key(key, _DirectoryPage)
    if cached is not None:
        return cached.items

    rows = await list_directory_db(
        q=q,
        domains=domains,
        skills=skills,
        sector=sector,
        country=country,
        program_id=program_id,
        stage=stage,
        mentors=mentors,
        limit=clamped_limit,
        offset=clamped_offset,
    )
    items = [_dto(row) for row in rows]
    if items:  # never cache empty
        await redis_update_key(key, _DirectoryPage(items=items), CACHE_TTL_SECONDS)
    return items
