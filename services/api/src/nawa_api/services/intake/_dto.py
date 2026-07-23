"""Shared intake DTOs — API-facing shapes derived from ORM rows."""

from __future__ import annotations


def rubric_dto(row) -> dict:
    return {
        "id": str(row.id),
        "program_id": str(row.program_id),
        "version": row.version,
        "name_ar": row.name_ar,
        "name_en": row.name_en,
        "criteria": row.criteria,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def application_dto(row) -> dict:
    return {
        "id": str(row.id),
        "cycle_id": str(row.cycle_id),
        "profile_id": str(row.profile_id) if row.profile_id else None,
        "applicant_name": row.applicant_name,
        "applicant_email": row.applicant_email,
        "source_language": row.source_language,
        "title": row.title,
        "summary": row.summary,
        "normalized": row.normalized,
        "status": row.status,
        "ai_total_score": row.ai_total_score,
        "submitted_at": row.submitted_at.isoformat(),
        "scored_at": row.scored_at.isoformat() if row.scored_at else None,
    }
