from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.site_config.upsert_site_config_db import upsert_site_config_db
from nawa_api.seed_data.taxonomy import SECTORS, SKILLS


async def seed_site_config(session: AsyncSession, *, ground_truth: dict) -> None:
    await upsert_site_config_db(
        key="taxonomy:sectors",
        value={s: {"label_en": s.replace("-", " ").title(), "label_ar": s} for s in SECTORS},
        session=session,
    )
    await upsert_site_config_db(
        key="taxonomy:skills",
        value={s: {"label_en": s.replace("-", " ").title(), "label_ar": s} for s in SKILLS},
        session=session,
    )
    await upsert_site_config_db(key="intake:dedup_threshold", value=0.83, session=session)
    await upsert_site_config_db(key="retention:audit_days", value=180, session=session)
    await upsert_site_config_db(key="rate_limiting_enabled", value=True, session=session)
    await upsert_site_config_db(key="audit_enabled", value=True, session=session)
    await upsert_site_config_db(key="maintenance_mode", value=False, session=session)
    await upsert_site_config_db(key="seed:ground_truth", value=ground_truth, session=session)
