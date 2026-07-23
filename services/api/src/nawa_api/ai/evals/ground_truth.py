"""Loader for the seeded answer key (05-ai-infrastructure.md §10).

The seed script stores ground truth in site_config under `seed:ground_truth`.
When the harness runs --against-seed it loads this alongside the checked-in
fixtures; in pure-fixture (CI) mode the key is optional.
"""

from __future__ import annotations

import json

from nawa_api.ai.evals.schemas import GroundTruth
from nawa_api.services.site_config.get_site_config import get_site_config

_KEY = "seed:ground_truth"


async def load_ground_truth() -> GroundTruth | None:
    config = await get_site_config()
    raw = config.get(_KEY)
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = json.loads(raw)
    return GroundTruth.model_validate(raw)
