"""observe_db — the context manager every *_db function wraps its body in."""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from nawa_api.metrics.registry import database_request_duration_seconds


@dataclass
class _Observation:
    success: bool = False


@contextmanager
def observe_db(*, operation: str, table: str, method: str) -> Iterator[_Observation]:
    """Times the wrapped block and always observes a sample, success or not.

    `operation` is one of read|write|delete|aggregate. Usage:

        with observe_db(operation="read", table="founder_profiles", method="get_x_db") as obs:
            ...
            obs.success = result is not None
    """
    start = time.perf_counter()
    obs = _Observation()
    try:
        yield obs
    finally:
        database_request_duration_seconds.labels(
            operation=operation,
            table=table,
            method=method,
            success="true" if obs.success else "false",
        ).observe(time.perf_counter() - start)
