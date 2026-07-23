"""Production boot guard: refuses to start with a weak signing key.

Runs at process start BEFORE the app factory and before any port binds. A
working placeholder JWT secret is silently catastrophic (every session forgeable),
so it is the one fatal check. Missing vendor creds only warn — they fail loudly
at first use via the ERR_*_NOT_CONFIGURED sentinels. No-op outside production.
"""

import sys

from nawa_api.runtime.settings import get_settings

_DEV_PLACEHOLDER = "change-me-in-development-only"
_MIN_SECRET_LEN = 32


def assert_production_config() -> None:
    settings = get_settings()
    if settings.environment != "production":
        return

    secret = settings.jwt_secret
    if (
        not secret
        or not secret.strip()
        or secret == _DEV_PLACEHOLDER
        or len(secret) < _MIN_SECRET_LEN
    ):
        print(
            "FATAL: JWT_SECRET is unset, blank, the dev placeholder, or shorter than "
            f"{_MIN_SECRET_LEN} characters. Refusing to start in production.",
            file=sys.stderr,
        )
        sys.exit(1)
