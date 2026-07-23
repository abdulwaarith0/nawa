import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.ai import AiCall
from nawa_api.utils.logger import get_logger


async def create_ai_call_db(
    *,
    task: str,
    provider: str,
    model: str,
    prompt_hash: str,
    prompt_version: str,
    status: str,
    tier: str | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    tokens_cached: int = 0,
    cost_estimate: float = 0,
    latency_ms: int = 0,
    error_code: str | None = None,
    request_id: str | None = None,
    cycle_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
    session: AsyncSession | None = None,
) -> AiCall | None:
    """Append-only ledger writer. Every LLM/embedding invocation logs one row
    here — cost/latency accounting depends on it never being skipped."""
    with observe_db(operation="write", table="ai_calls", method="create_ai_call_db") as obs:
        try:
            async with use_session(session) as s:
                row = AiCall(
                    task=task,
                    provider=provider,
                    model=model,
                    tier=tier,
                    prompt_hash=prompt_hash,
                    prompt_version=prompt_version,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    tokens_cached=tokens_cached,
                    cost_estimate=cost_estimate,
                    latency_ms=latency_ms,
                    status=status,
                    error_code=error_code,
                    request_id=request_id,
                    cycle_id=cycle_id,
                    created_by=created_by,
                    subject_type=subject_type,
                    subject_id=subject_id,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_ai_call_db", exc_info=True)
            obs.success = False
            return None
