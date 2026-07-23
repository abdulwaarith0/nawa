"""nawa_api package.

Forces the SelectorEventLoop policy on Windows at import time: asyncpg
needs socket primitives the default ProactorEventLoop doesn't implement.
Must run before any event loop is created, so it lives at the top of the
package `__init__` rather than in any one entrypoint.
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main() -> None:
    print("Hello from nawa-api!")
