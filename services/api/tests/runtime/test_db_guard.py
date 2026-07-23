from nawa_api.runtime.db_guard import (
    SEED_SAFE_DB_NAME,
    TEST_DB_PREFIX,
    is_seed_safe_db_name,
)


def test_constants_are_the_documented_values():
    assert SEED_SAFE_DB_NAME == "nawa_dev"
    assert TEST_DB_PREFIX == "nawa_test_"


def test_dev_db_name_is_safe():
    assert is_seed_safe_db_name("nawa_dev") is True


def test_test_prefixed_names_are_safe():
    assert is_seed_safe_db_name("nawa_test_abc123") is True
    assert is_seed_safe_db_name("nawa_test_") is True


def test_none_is_not_safe():
    assert is_seed_safe_db_name(None) is False


def test_production_like_names_are_not_safe():
    assert is_seed_safe_db_name("nawa_prod") is False
    assert is_seed_safe_db_name("postgres") is False
    assert is_seed_safe_db_name("nawa_development") is False


def test_prefix_must_match_from_the_start():
    assert is_seed_safe_db_name("something_nawa_test_x") is False
