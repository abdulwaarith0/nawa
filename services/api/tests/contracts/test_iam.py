import pytest

from nawa_api.contracts.iam import (
    CATALOG,
    PERMISSION_META,
    Permission,
    compile_statements,
    describe_action,
    expand_actions,
    validate_action,
)


def test_catalog_contains_console_and_feature_permissions():
    assert "nawa:console:intake" in CATALOG
    assert "nawa:iam:manage" in CATALOG
    assert Permission.COMMUNITY_READ == "nawa:community:read"
    assert Permission.INTAKE_OVERRIDE == "nawa:intake:override"


def test_permission_meta_covers_every_catalog_entry():
    assert set(PERMISSION_META.keys()) == CATALOG


def test_expand_star_allows_everything():
    assert expand_actions(["*"]) == CATALOG


def test_expand_domain_wildcard():
    intake = expand_actions(["nawa:intake:*"])
    assert Permission.INTAKE_INGEST in intake
    assert Permission.INTAKE_OVERRIDE in intake
    assert Permission.COMMUNITY_READ not in intake


def test_expand_exact_action():
    assert expand_actions(["nawa:community:read"]) == {"nawa:community:read"}


def test_expand_rejects_invalid_action():
    with pytest.raises(ValueError):
        expand_actions(["not:a:valid:action"])


def test_compile_allow_then_deny_removes_only_denied():
    statements = [
        {"effect": "Allow", "actions": ["nawa:intake:*"]},
        {"effect": "Deny", "actions": ["nawa:intake:override"]},
    ]
    result = compile_statements(statements)
    assert Permission.INTAKE_INGEST in result
    assert Permission.INTAKE_OVERRIDE not in result


def test_compile_star_allow():
    result = compile_statements([{"effect": "Allow", "actions": ["*"]}])
    assert result == CATALOG


def test_compile_deny_star_wins_over_all_allows():
    statements = [
        {"effect": "Allow", "actions": ["*"]},
        {"effect": "Deny", "actions": ["*"]},
    ]
    assert compile_statements(statements) == set()


def test_compile_empty_statements_is_empty_set():
    assert compile_statements([]) == set()


def test_compile_unions_multiple_allows():
    statements = [
        {"effect": "Allow", "actions": ["nawa:community:read"]},
        {"effect": "Allow", "actions": ["nawa:profiles:write"]},
    ]
    result = compile_statements(statements)
    assert result == {"nawa:community:read", "nawa:profiles:write"}


def test_validate_action_accepts_star_wildcard_and_exact():
    assert validate_action("*") is True
    assert validate_action("nawa:intake:*") is True
    assert validate_action("nawa:intake:override") is True
    assert validate_action("nawa:bogus:action") is False
    assert validate_action("garbage") is False


def test_describe_action_explains_wildcards():
    assert "area" in describe_action("nawa:intake:*").lower()
    assert describe_action("nawa:community:read") == PERMISSION_META["nawa:community:read"]["label"]
