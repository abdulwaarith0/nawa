"""Decided-shortlist XLSX export (06-intake-copilot.md §6.1).

Generates the decided shortlist (every application past `scored` — i.e. one
a human has actually decided on) as an XLSX workbook, uploads it through the
object-storage pipeline under `intake/exports/<cycle_id>/<ts>.xlsx`, and
returns a presigned GET URL. Not cached — each export is a fresh snapshot.

Registered as an arq job (so it CAN run on the worker later), but called
directly from the route for now — the same deferral chunks 5/6/8/9 already
made for other write operations, since a real arq-pool-enqueue-from-route
helper is still out of scope.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO

import openpyxl

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.db.intake.get_active_rubric_db import get_active_rubric_db
from nawa_api.db.intake.list_decided_applications_for_export_db import (
    list_decided_applications_for_export_db,
)
from nawa_api.db.intake.list_scorecard_criteria_db import list_scorecard_criteria_db
from nawa_api.db.programs.get_program_cycle_db import get_program_cycle_db
from nawa_api.db.users.get_user_by_id_db import get_user_by_id_db
from nawa_api.runtime.storage import get_storage_provider

PRESIGN_TTL_SECONDS = 3600
_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_BASE_HEADERS = ("Rank", "Applicant", "Title", "Language", "Country", "Total Score")
_TAIL_HEADERS = ("Hidden Gem", "Decision", "Decision Reason", "Decider", "Decided At")


def _storage_key(cycle_id: uuid.UUID, *, now: datetime) -> str:
    return f"intake/exports/{cycle_id}/{now.strftime('%Y%m%dT%H%M%SZ')}.xlsx"


async def _deciders_by_id(rows) -> dict[uuid.UUID, str]:
    decider_ids = {decision["decided_by"] for _a, _s, decision in rows if decision is not None}
    deciders: dict[uuid.UUID, str] = {}
    for decider_id in decider_ids:
        user = await get_user_by_id_db(user_id=decider_id)
        deciders[decider_id] = user.full_name if user is not None else str(decider_id)
    return deciders


async def export_shortlist(_ctx: dict | None = None, cycle_id: str | uuid.UUID = "") -> dict:
    cid = uuid.UUID(str(cycle_id))
    cycle = await get_program_cycle_db(cycle_id=cid)
    if cycle is None:
        raise ERR_NOT_FOUND

    rubric = await get_active_rubric_db(program_id=cycle.program_id)
    criterion_keys = [c["key"] for c in rubric.criteria] if rubric is not None else []
    rows = await list_decided_applications_for_export_db(
        cycle_id=cid, rubric_id=rubric.id if rubric is not None else None
    )

    scorecard_ids = [scorecard.id for _a, scorecard, _d in rows if scorecard is not None]
    criteria_rows = await list_scorecard_criteria_db(scorecard_ids=scorecard_ids)
    criteria_by_scorecard: dict[uuid.UUID, dict[str, float]] = {}
    for criterion in criteria_rows:
        criteria_by_scorecard.setdefault(criterion.scorecard_id, {})[
            criterion.criterion_key
        ] = criterion.score
    deciders = await _deciders_by_id(rows)

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Shortlist"
    sheet.append([*_BASE_HEADERS, *criterion_keys, *_TAIL_HEADERS])
    for index, (application, scorecard, decision) in enumerate(rows, start=1):
        criteria = criteria_by_scorecard.get(scorecard.id, {}) if scorecard else {}
        row = [
            index,
            application.applicant_name,
            application.title,
            application.source_language,
            application.normalized.get("country"),
            application.ai_total_score,
        ]
        row.extend(criteria.get(key) for key in criterion_keys)
        row.extend(
            [
                scorecard.hidden_gem if scorecard else False,
                decision["decision"] if decision else None,
                decision["reason"] if decision else None,
                deciders.get(decision["decided_by"]) if decision else None,
                decision["created_at"].isoformat() if decision else None,
            ]
        )
        sheet.append(row)

    buffer = BytesIO()
    workbook.save(buffer)

    storage_key = _storage_key(cid, now=datetime.now(UTC))
    storage = get_storage_provider()
    await storage.put_object(storage_key, buffer.getvalue(), content_type=_CONTENT_TYPE)
    url = await storage.presign_get_url(storage_key, expires_seconds=PRESIGN_TTL_SECONDS)

    return {"row_count": len(rows), "url": url, "storage_key": storage_key}
