"""Shared membership-request DTO — the API-facing shape derived from the ORM row."""

from __future__ import annotations


def membership_request_dto(row) -> dict:
    return {
        "id": str(row.id),
        "full_name": row.full_name,
        "email": row.email,
        "organization": row.organization,
        "reason": row.reason,
        "status": row.status,
        "reviewed_by_user_id": str(row.reviewed_by_user_id) if row.reviewed_by_user_id else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "created_at": row.created_at.isoformat(),
    }
