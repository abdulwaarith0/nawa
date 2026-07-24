"""Response envelope helpers. Every endpoint returns exactly:

{"code": <int mirrors HTTP status>, "message": <str>, "data": <payload | null>}
"""

from typing import Any


def ok(data: Any) -> dict:
    return {"code": 200, "message": "OK", "data": data}


def created(data: Any) -> dict:
    return {"code": 201, "message": "Created", "data": data}


def accepted(data: Any) -> dict:
    return {"code": 202, "message": "Accepted", "data": data}


def fail(code: int, message: str) -> dict:
    return {"code": code, "message": message, "data": None}
