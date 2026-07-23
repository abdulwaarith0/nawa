"""Tolerant bulk-upload parser (06-intake-copilot.md §2.1).

Parses CSV / XLSX / JSON into canonical application rows. A `column_map` maps
source columns to canonical fields (applicant_name/applicant_email/phone/country)
or to question keys (which become original_answers entries); any source column
NOT in the map is preserved into raw_extra so no applicant data is silently
dropped.
"""

from __future__ import annotations

import csv
import io
import json

from pydantic import BaseModel, Field

from nawa_api.contracts.errors import ERR_INVALID_FIELDS

_CANONICAL = {"applicant_name", "applicant_email", "phone", "country"}


class ParsedApplication(BaseModel):
    applicant_name: str
    applicant_email: str
    phone: str | None = None
    country: str | None = None
    original_answers: dict[str, str] = Field(default_factory=dict)
    raw_extra: dict[str, str] = Field(default_factory=dict)


def _rows(content: bytes, filename: str) -> list[dict[str, str]]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    try:
        if ext == "csv":
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            return [{k: (v or "") for k, v in row.items() if k is not None} for row in reader]
        if ext == "json":
            data = json.loads(content.decode("utf-8"))
            if not isinstance(data, list):
                raise ERR_INVALID_FIELDS
            return [{str(k): "" if v is None else str(v) for k, v in obj.items()} for obj in data]
        if ext == "xlsx":
            import openpyxl

            workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            grid = list(workbook.active.iter_rows(values_only=True))
            if not grid:
                return []
            headers = [str(h) if h is not None else "" for h in grid[0]]
            return [
                {headers[i]: "" if cell is None else str(cell) for i, cell in enumerate(row)}
                for row in grid[1:]
            ]
    except ERR_INVALID_FIELDS.__class__:
        raise
    except Exception as exc:
        raise ERR_INVALID_FIELDS from exc
    raise ERR_INVALID_FIELDS  # unsupported extension


def _map_row(row: dict[str, str], column_map: dict[str, str]) -> ParsedApplication:
    fields: dict[str, str] = {}
    answers: dict[str, str] = {}
    extra: dict[str, str] = {}
    for source_col, value in row.items():
        target = column_map.get(source_col)
        if target is None:
            extra[source_col] = value
        elif target in _CANONICAL:
            fields[target] = value
        else:
            answers[target] = value
    if not fields.get("applicant_name") or not fields.get("applicant_email"):
        raise ERR_INVALID_FIELDS  # every application needs at least a name + email
    return ParsedApplication(**fields, original_answers=answers, raw_extra=extra)


def parse_upload(
    content: bytes, filename: str, column_map: dict[str, str]
) -> list[ParsedApplication]:
    return [_map_row(row, column_map) for row in _rows(content, filename)]
