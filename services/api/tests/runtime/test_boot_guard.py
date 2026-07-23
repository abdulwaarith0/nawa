import subprocess
import sys

BAD_SECRETS = ["", "   ", "change-me-in-development-only", "x" * 31]
STRONG_SECRET = "x" * 64

_CALL = (
    "from nawa_api.runtime.boot_guard import assert_production_config; assert_production_config()"
)


def _run(env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _CALL],
        env=env,
        capture_output=True,
        text=True,
    )


def test_production_boot_refuses_weak_jwt_secret():
    for secret in BAD_SECRETS:
        proc = _run(
            {"ENVIRONMENT": "production", "JWT_SECRET": secret, "SYSTEMROOT": _systemroot()}
        )
        assert proc.returncode == 1, f"secret {secret!r} should fail"
        combined = proc.stderr + proc.stdout
        assert "JWT_SECRET" in combined
        # Never print the secret value (blank/whitespace secrets are trivially absent).
        assert secret not in combined or secret.strip() == ""


def test_production_boot_accepts_strong_secret():
    proc = _run(
        {"ENVIRONMENT": "production", "JWT_SECRET": STRONG_SECRET, "SYSTEMROOT": _systemroot()}
    )
    assert proc.returncode == 0


def test_non_production_is_a_noop_even_with_weak_secret():
    proc = _run({"ENVIRONMENT": "development", "JWT_SECRET": "", "SYSTEMROOT": _systemroot()})
    assert proc.returncode == 0


def _systemroot() -> str:
    # Windows needs SYSTEMROOT on PATH-less subprocess envs to import stdlib
    # extension modules; harmless elsewhere.
    import os

    return os.environ.get("SYSTEMROOT", "")
