"""Record a Midnight zero-knowledge eligibility proof against an application.

The proof itself is produced client-side by the midnight-eligibility contract
(see /midnight-eligibility at the repo root): the applicant proves they meet a
program's public criteria — a minimum age and a prior-funding cap — without ever
revealing their actual age or funding. All that reaches NAWA is a verifiable
reference (the deployed contract address and the proof transaction id) plus the
verdict. We write that reference to the immutable audit log, so a human decision
can cite that the applicant cleared the bar without NAWA ever holding the
sensitive inputs behind it. This fits the "AI never rejects, humans decide"
model: the proof is evidence in the record, not an automated gate.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_INVALID_FIELDS, ERR_NOT_FOUND
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.services.audit.create_audit_log import create_audit_log
from nawa_api.utils.request_context import request_id_var

_VERDICTS = frozenset({"eligible", "ineligible"})


async def record_eligibility_proof(
    *,
    application_id: uuid.UUID,
    contract_address: str,
    tx_id: str,
    verdict: str,
    network: str,
    min_age: int | None,
    max_prior_funding: int | None,
    recorded_by: uuid.UUID,
) -> dict:
    if verdict not in _VERDICTS:
        raise ERR_INVALID_FIELDS
    if not contract_address.strip() or not tx_id.strip():
        raise ERR_INVALID_FIELDS

    application = await get_application_db(application_id=application_id)
    if application is None:
        raise ERR_NOT_FOUND

    proof_ref = f"{contract_address}@{tx_id}"
    await create_audit_log(
        actor_id=recorded_by,
        action="intake.eligibility.proof",
        target_type="intake_application",
        target_id=application_id,
        request_id=request_id_var.get(),
        body={
            "proof_ref": proof_ref,
            "contract_address": contract_address,
            "tx_id": tx_id,
            "verdict": verdict,
            "network": network,
            "criteria": {
                "min_age": min_age,
                "max_prior_funding": max_prior_funding,
            },
        },
    )
    return {
        "application_id": str(application_id),
        "proof_ref": proof_ref,
        "verdict": verdict,
        "network": network,
    }
