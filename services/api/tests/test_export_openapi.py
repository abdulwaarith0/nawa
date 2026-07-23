"""The OpenAPI/iam.ts export must build offline (no DB/Redis) and emit valid
artifacts — it's the head of the TS contracts pipeline."""

import json

from nawa_api.scripts import export_openapi


def test_export_openapi_json_writes_valid_schema():
    export_openapi.export_openapi_json()
    assert export_openapi._OPENAPI_JSON.exists()
    schema = json.loads(export_openapi._OPENAPI_JSON.read_text(encoding="utf-8"))
    assert schema["openapi"].startswith("3.")
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/iam/policies" in schema["paths"]


def test_export_iam_ts_mirrors_the_python_catalog():
    from nawa_api.contracts.iam import PERMISSION_META

    export_openapi.export_iam_ts()
    assert export_openapi._IAM_TS.exists()
    ts = export_openapi._IAM_TS.read_text(encoding="utf-8")
    assert "export const PERMISSIONS" in ts
    assert "export function homeForPermissions" in ts
    # every permission from the Python catalog appears in the generated TS
    for perm in PERMISSION_META:
        assert perm in ts


def test_main_runs_both_exports(capsys):
    export_openapi.main()
    out = capsys.readouterr().out
    assert "iam.ts" in out
    assert "openapi.json" in out
