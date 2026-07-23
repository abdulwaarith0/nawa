"""Exit 0 once Postgres accepts a connection, non-zero otherwise. Used by the
Docker entrypoint to wait for the database before migrating."""

import asyncio
import sys

import nawa_api  # noqa: F401  (Windows event-loop policy)
from nawa_api.runtime.postgres import connect_postgres


def main() -> None:
    try:
        asyncio.run(connect_postgres(timeout_seconds=3))
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
