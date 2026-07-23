"""The ONLY definition of the safe-database rule.

Both nawa_api.seed and the pytest harness fixtures import
`is_seed_safe_db_name` — never a copied string literal — so the two
places that can wipe data agree on exactly one safety rule.
"""

SEED_SAFE_DB_NAME = "nawa_dev"
TEST_DB_PREFIX = "nawa_test_"


def is_seed_safe_db_name(name: str | None) -> bool:
    return name is not None and (name == SEED_SAFE_DB_NAME or name.startswith(TEST_DB_PREFIX))
