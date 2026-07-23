from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.resources.create_resource_chunk_db import create_resource_chunk_db
from nawa_api.db.resources.create_resource_db import create_resource_db
from nawa_api.seed_data.embeddings import EMBEDDING_MODEL, deterministic_vector, source_hash
from nawa_api.seed_data.taxonomy import RESOURCE_TOPICS

_RNG_SEED = 20260722
_RESOURCES_PER_TOPIC = 3
_CHUNKS_PER_RESOURCE = 10

_KIND_BY_TOPIC_INDEX = [
    "handbook",
    "lab_capability",
    "policy",
    "lab_capability",
    "mentor_bio",
    "mentor_bio",
    "faq",
    "policy",
    "guide",
    "guide",
]

_CHUNK_TEMPLATES_EN = [
    "Section {n}: overview of {topic} covering scope, eligibility, and process steps relevant "
    "to founders applying to Program programs.",
    "Section {n}: detailed guidance on {topic}, including timelines, required documentation, "
    "and points of contact for follow-up questions.",
    "Section {n}: frequently encountered issues related to {topic} and how program staff "
    "typically resolve them for program participants.",
]
_CHUNK_TEMPLATES_AR = [
    "القسم {n}: نظرة عامة على {topic} تغطي النطاق وشروط الأهلية وخطوات العملية للمؤسسين "
    "المتقدمين لبرامج مركز قطر لعلوم وتكنولوجيا.",
    "القسم {n}: إرشادات مفصلة حول {topic} تشمل الجداول الزمنية والمستندات المطلوبة وجهات "
    "الاتصال للمتابعة.",
]


async def seed_resources(session: AsyncSession) -> None:
    rng = random.Random(_RNG_SEED + 2)

    for topic_index, (title_en, title_ar) in enumerate(RESOURCE_TOPICS):
        kind = _KIND_BY_TOPIC_INDEX[topic_index % len(_KIND_BY_TOPIC_INDEX)]
        for variant in range(_RESOURCES_PER_TOPIC):
            language = "ar" if variant % 2 == 0 else "en"
            title = f"{title_ar} {variant + 1}" if language == "ar" else f"{title_en} {variant + 1}"
            resource = await create_resource_db(
                kind=kind,
                title_ar=title if language == "ar" else None,
                title_en=title if language == "en" else None,
                language=language,
                status="live",
                tags=[kind, "program"],
                session=session,
            )

            for c in range(_CHUNKS_PER_RESOURCE):
                templates = _CHUNK_TEMPLATES_AR if language == "ar" else _CHUNK_TEMPLATES_EN
                content = rng.choice(templates).format(n=c + 1, topic=title)
                content_key = f"resource-chunk-{resource.id}-{c}"
                await create_resource_chunk_db(
                    resource_id=resource.id,
                    chunk_index=c,
                    content=content,
                    token_count=len(content.split()),
                    source_hash=source_hash(content_key),
                    language=language,
                    heading_path=[title, f"Section {c + 1}"],
                    embedding=deterministic_vector(content_key),
                    embedding_model=EMBEDDING_MODEL,
                    session=session,
                )
