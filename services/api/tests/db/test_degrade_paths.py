"""Sweeps every db-layer function's exception-handling branch in one place.

Each *_db function's degrade path (swallow, log, return the safe fallback)
is identical in shape, so rather than duplicate a bespoke test per file this
monkeypatches session_factory to fail once and drives every function through
it — proving each one actually degrades (None/[]/False) instead of raising,
per the architecture's "errors are swallowed" contract.
"""

import uuid
from datetime import UTC, date, datetime

import pytest

from nawa_api.db.ai_calls.create_ai_call_db import create_ai_call_db
from nawa_api.db.audit.create_audit_log_db import create_audit_log_db
from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.cohorts.get_cohort_db import get_cohort_db
from nawa_api.db.cohorts.list_cohort_members_db import list_cohort_members_db
from nawa_api.db.cohorts.list_cohorts_db import list_cohorts_db
from nawa_api.db.cohorts.upsert_cohort_member_db import upsert_cohort_member_db
from nawa_api.db.community.create_mentorship_db import create_mentorship_db
from nawa_api.db.community.create_opportunity_db import create_opportunity_db
from nawa_api.db.community.create_opportunity_match_db import create_opportunity_match_db
from nawa_api.db.community.create_request_db import create_request_db
from nawa_api.db.community.create_request_match_db import create_request_match_db
from nawa_api.db.community.list_opportunities_db import list_opportunities_db
from nawa_api.db.community.list_requests_db import list_requests_db
from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.create_group_db import create_group_db
from nawa_api.db.iam.create_policy_db import create_policy_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.iam.get_policy_by_name_db import get_policy_by_name_db
from nawa_api.db.iam.list_groups_db import list_groups_db
from nawa_api.db.iam.list_policies_db import list_policies_db
from nawa_api.db.iam.list_user_group_ids_db import list_user_group_ids_db
from nawa_api.db.intake.count_higher_scoring_applications_db import (
    count_higher_scoring_applications_db,
)
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_application_document_db import create_application_document_db
from nawa_api.db.intake.create_application_embedding_db import create_application_embedding_db
from nawa_api.db.intake.create_application_upload_db import create_application_upload_db
from nawa_api.db.intake.create_decision_db import create_decision_db
from nawa_api.db.intake.create_dedup_match_db import create_dedup_match_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.get_active_rubric_db import get_active_rubric_db
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.intake.get_application_embedding_db import get_application_embedding_db
from nawa_api.db.intake.list_application_documents_db import list_application_documents_db
from nawa_api.db.intake.list_applications_by_email_db import list_applications_by_email_db
from nawa_api.db.intake.list_applications_db import list_applications_db
from nawa_api.db.intake.list_decided_applications_for_export_db import (
    list_decided_applications_for_export_db,
)
from nawa_api.db.intake.list_decisions_for_application_db import (
    list_decisions_for_application_db,
)
from nawa_api.db.intake.list_dedup_matches_db import list_dedup_matches_db
from nawa_api.db.intake.list_pending_dedup_matches_for_applications_db import (
    list_pending_dedup_matches_for_applications_db,
)
from nawa_api.db.intake.list_scorecard_criteria_db import list_scorecard_criteria_db
from nawa_api.db.intake.list_scorecards_for_application_db import (
    list_scorecards_for_application_db,
)
from nawa_api.db.intake.list_shortlist_db import list_shortlist_db
from nawa_api.db.intake.list_similar_applications_db import list_similar_applications_db
from nawa_api.db.intake.update_application_decision_status_db import (
    update_application_decision_status_db,
)
from nawa_api.db.intake.update_application_profile_link_db import (
    update_application_profile_link_db,
)
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.intake.update_scorecard_hidden_gem_db import update_scorecard_hidden_gem_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.journey.create_assistant_message_db import create_assistant_message_db
from nawa_api.db.journey.create_assistant_thread_db import create_assistant_thread_db
from nawa_api.db.journey.create_digest_db import create_digest_db
from nawa_api.db.journey.create_milestone_db import create_milestone_db
from nawa_api.db.journey.create_milestone_progress_db import create_milestone_progress_db
from nawa_api.db.journey.list_milestone_progress_db import list_milestone_progress_db
from nawa_api.db.journey.list_milestones_db import list_milestones_db
from nawa_api.db.kpi.create_kpi_definition_db import create_kpi_definition_db
from nawa_api.db.kpi.create_kpi_entry_db import create_kpi_entry_db
from nawa_api.db.kpi.list_kpi_definitions_db import list_kpi_definitions_db
from nawa_api.db.kpi.list_kpi_series_db import list_kpi_series_db
from nawa_api.db.kpi.refresh_kpi_snapshot_db import refresh_kpi_snapshot_db
from nawa_api.db.notifications.create_notification_db import create_notification_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.profiles.get_founder_profile_by_user_id_db import (
    get_founder_profile_by_user_id_db,
)
from nawa_api.db.profiles.get_profile_by_handle_db import get_profile_by_handle_db
from nawa_api.db.profiles.get_profile_by_id_any_status_db import get_profile_by_id_any_status_db
from nawa_api.db.profiles.list_profile_program_history_db import (
    list_profile_program_history_db,
)
from nawa_api.db.profiles.list_profiles_db import list_profiles_db
from nawa_api.db.profiles.set_profile_embedding_db import set_profile_embedding_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.programs.get_program_by_slug_db import get_program_by_slug_db
from nawa_api.db.programs.get_program_cycle_db import get_program_cycle_db
from nawa_api.db.programs.get_program_db import get_program_db
from nawa_api.db.programs.list_program_cycles_db import list_program_cycles_db
from nawa_api.db.programs.list_programs_db import list_programs_db
from nawa_api.db.reports.create_anomaly_db import create_anomaly_db
from nawa_api.db.reports.create_check_in_db import create_check_in_db
from nawa_api.db.reports.create_report_db import create_report_db
from nawa_api.db.resources.create_resource_chunk_db import create_resource_chunk_db
from nawa_api.db.resources.create_resource_db import create_resource_db
from nawa_api.db.resources.list_resources_db import list_resources_db
from nawa_api.db.resources.list_similar_chunks_db import list_similar_chunks_db
from nawa_api.db.site_config.get_site_config_db import get_site_config_db
from nawa_api.db.site_config.upsert_site_config_db import upsert_site_config_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db.users.get_user_by_email_db import get_user_by_email_db
from nawa_api.db.users.get_user_by_identifier_db import get_user_by_identifier_db
from nawa_api.db.users.list_users_db import list_users_db
from nawa_api.db.users.update_user_db import update_user_db

_ID = uuid.uuid4()
_NOW = datetime.now(UTC)
_DIM_VEC = [0.0] * 8  # length doesn't matter — session_factory raises first


@pytest.fixture(autouse=True)
def _broken_session_factory(monkeypatch):
    def _raise():
        raise RuntimeError("db unreachable")

    monkeypatch.setattr("nawa_api.db.utils.session_factory", _raise)


# (callable, kwargs, expected degraded return value)
_CASES = [
    (
        create_user_db,
        dict(email="a@example.com", username="a", password_hash="h", full_name="A"),
        None,
    ),
    (get_user_by_email_db, dict(email="a@example.com"), None),
    (get_user_by_identifier_db, dict(identifier="a@example.com"), None),
    (list_users_db, dict(), []),
    (update_user_db, dict(user_id=_ID, full_name="X"), False),
    (create_policy_db, dict(name="P", statements=[]), None),
    (get_policy_by_name_db, dict(name="P"), None),
    (list_policies_db, dict(), []),
    (create_group_db, dict(name="G"), None),
    (get_group_by_name_db, dict(name="G"), None),
    (list_groups_db, dict(), []),
    (add_group_member_db, dict(group_id=_ID, user_id=_ID), None),
    (list_user_group_ids_db, dict(user_id=_ID), []),
    (create_program_db, dict(slug="s", kind="competition"), None),
    (get_program_by_slug_db, dict(slug="s"), None),
    (get_program_db, dict(program_id=_ID), None),
    (list_programs_db, dict(), []),
    (create_program_cycle_db, dict(program_id=_ID, slug="s"), None),
    (list_program_cycles_db, dict(), []),
    (get_program_cycle_db, dict(cycle_id=_ID), None),
    (create_cohort_db, dict(cycle_id=_ID, program_manager_user_id=_ID, starts_at=_NOW), None),
    (get_cohort_db, dict(cohort_id=_ID), None),
    (list_cohorts_db, dict(), []),
    (create_cohort_member_db, dict(cohort_id=_ID, profile_id=_ID), None),
    (upsert_cohort_member_db, dict(cohort_id=_ID, profile_id=_ID), False),
    (list_cohort_members_db, dict(cohort_id=_ID), []),
    (create_founder_profile_db, dict(user_id=_ID, handle="h"), None),
    (get_founder_profile_by_user_id_db, dict(user_id=_ID), None),
    (get_profile_by_handle_db, dict(handle="h"), None),
    (get_profile_by_id_any_status_db, dict(profile_id=_ID), None),
    (list_profiles_db, dict(), []),
    (list_profile_program_history_db, dict(profile_id=_ID), []),
    (
        set_profile_embedding_db,
        dict(profile_id=_ID, embedding=_DIM_VEC, embedding_model="m"),
        False,
    ),
    (create_rubric_db, dict(program_id=_ID, version=1, criteria=[]), None),
    (get_active_rubric_db, dict(program_id=_ID), None),
    (
        create_application_upload_db,
        dict(
            cycle_id=_ID,
            storage_key="k",
            file_name="f",
            mime_type="t",
            size_bytes=1,
            uploaded_by_user_id=_ID,
        ),
        None,
    ),
    (
        create_application_db,
        dict(
            cycle_id=_ID,
            applicant_name="n",
            applicant_email="e@example.com",
            source_language="en",
            original_answers={},
        ),
        None,
    ),
    (get_application_db, dict(application_id=_ID), None),
    (list_applications_db, dict(cycle_id=_ID), []),
    (
        create_application_document_db,
        dict(application_id=_ID, storage_key="k", file_name="f", mime_type="t", size_bytes=1),
        None,
    ),
    (
        create_scorecard_db,
        dict(
            application_id=_ID,
            rubric_id=_ID,
            rubric_version=1,
            prompt_version="v",
            source="ai",
            total_score=1.0,
        ),
        None,
    ),
    (list_scorecards_for_application_db, dict(application_id=_ID), []),
    (list_application_documents_db, dict(application_id=_ID), []),
    (
        update_application_scoring_db,
        dict(application_id=_ID, total_score=1.0),
        False,
    ),
    (
        update_scorecard_hidden_gem_db,
        dict(scorecard_id=_ID, hidden_gem=True, hidden_gem_reason_ar="a", hidden_gem_reason_en="e"),
        False,
    ),
    (
        create_scorecard_criterion_db,
        dict(scorecard_id=_ID, criterion_key="k", score=1.0, weight=1.0),
        None,
    ),
    (
        create_application_embedding_db,
        dict(application_id=_ID, embedding=_DIM_VEC, embedding_model="m", source_hash="h"),
        False,
    ),
    (get_application_embedding_db, dict(application_id=_ID), None),
    (list_similar_applications_db, dict(application_id=_ID), []),
    (list_applications_by_email_db, dict(applicant_email="a@example.com"), []),
    (
        create_dedup_match_db,
        dict(application_id=_ID, matched_application_id=_ID, similarity=0.9),
        None,
    ),
    (
        upsert_dedup_match_db,
        dict(application_id=_ID, matched_application_id=_ID, similarity=0.9),
        False,
    ),
    (create_decision_db, dict(application_id=_ID, decided_by=_ID, decision="shortlist"), None),
    (list_decisions_for_application_db, dict(application_id=_ID), []),
    (
        list_decided_applications_for_export_db,
        dict(cycle_id=_ID, rubric_id=_ID),
        [],
    ),
    (count_higher_scoring_applications_db, dict(cycle_id=_ID, total_score=1.0), 0),
    (update_application_profile_link_db, dict(application_id=_ID, profile_id=_ID), False),
    (
        update_application_decision_status_db,
        dict(application_id=_ID, status="shortlisted"),
        False,
    ),
    (list_dedup_matches_db, dict(application_id=_ID), []),
    (
        list_pending_dedup_matches_for_applications_db,
        dict(application_ids=[_ID]),
        [],
    ),
    (list_scorecard_criteria_db, dict(scorecard_ids=[_ID]), []),
    (list_shortlist_db, dict(cycle_id=_ID, rubric_id=_ID), []),
    (create_milestone_db, dict(program_id=_ID, sequence=1), None),
    (list_milestones_db, dict(), []),
    (
        create_milestone_progress_db,
        dict(milestone_id=_ID, cohort_member_id=_ID, founder_profile_id=_ID),
        None,
    ),
    (list_milestone_progress_db, dict(), []),
    (create_resource_db, dict(kind="handbook"), None),
    (list_resources_db, dict(), []),
    (
        create_resource_chunk_db,
        dict(resource_id=_ID, chunk_index=0, content="c", token_count=1, source_hash="h"),
        None,
    ),
    (list_similar_chunks_db, dict(query_embedding=_DIM_VEC), []),
    (create_assistant_thread_db, dict(user_id=_ID), None),
    (create_assistant_message_db, dict(thread_id=_ID, role="user", content="c"), None),
    (
        create_digest_db,
        dict(
            kind="cohort",
            scope_type="cohort",
            scope_id=_ID,
            period_start=date.today(),
            period_end=date.today(),
        ),
        None,
    ),
    (create_request_db, dict(profile_id=_ID, kind="talent"), None),
    (list_requests_db, dict(), []),
    (create_request_match_db, dict(request_id=_ID, profile_id=_ID, score=0.5), None),
    (create_opportunity_db, dict(posted_by_user_id=_ID, kind="internship"), None),
    (list_opportunities_db, dict(), []),
    (create_opportunity_match_db, dict(opportunity_id=_ID, profile_id=_ID, score=0.5), None),
    (create_mentorship_db, dict(mentor_profile_id=_ID, mentee_profile_id=uuid.uuid4()), None),
    (create_kpi_definition_db, dict(key="k"), None),
    (list_kpi_definitions_db, dict(), []),
    (
        create_kpi_entry_db,
        dict(
            profile_id=_ID,
            kpi_definition_id=_ID,
            period_start=date.today(),
            value=1.0,
            confirmed_at=_NOW,
        ),
        False,
    ),
    (list_kpi_series_db, dict(profile_id=_ID, kpi_definition_id=_ID), []),
    (refresh_kpi_snapshot_db, dict(profile_id=_ID), False),
    (create_check_in_db, dict(profile_id=_ID, period_start=date.today()), None),
    (
        create_report_db,
        dict(
            kind="founder_monthly",
            subject_type="profile",
            period_start=date.today(),
            period_end=date.today(),
        ),
        None,
    ),
    (
        create_anomaly_db,
        dict(
            profile_id=_ID,
            kind="runway",
            severity="warning",
            window_start=date.today(),
            window_end=date.today(),
            dedupe_key="k",
        ),
        False,
    ),
    (create_notification_db, dict(user_id=_ID, kind="k"), None),
    (
        create_audit_log_db,
        dict(action="a", target_type="t"),
        None,
    ),
    (
        create_ai_call_db,
        dict(task="t", provider="p", model="m", prompt_hash="h", prompt_version="v", status="ok"),
        None,
    ),
    (upsert_site_config_db, dict(key="k", value={}), False),
    (get_site_config_db, dict(key="k"), None),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fn,kwargs,expected", _CASES, ids=[c[0].__name__ for c in _CASES])
async def test_db_function_degrades_on_broken_session_factory(fn, kwargs, expected):
    result = await fn(**kwargs)
    assert result == expected
