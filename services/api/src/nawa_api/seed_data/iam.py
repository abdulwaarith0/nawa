"""IAM seed: seven canonical groups, matching policies, one login per group.

Slice 04's boot seeder will upsert-by-name over these managed rows, so the
names here are a fixed contract the later slice must match exactly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.create_group_db import create_group_db
from nawa_api.db.iam.create_policy_db import create_policy_db
from nawa_api.db.users.create_user_db import create_user_db

# (identifier, group name) — the exact contract 10-testing-validation.md's
# Playwright fixtures hardcode.
CREDENTIALS_TABLE: list[tuple[str, str]] = [
    ("admin@nawa.local", "Administrators"),
    ("manager@nawa.local", "Program Managers"),
    ("reviewer@nawa.local", "Reviewers"),
    ("founder@nawa.local", "Founders"),
    ("mentor@nawa.local", "Mentors"),
    ("moderator@nawa.local", "Moderators"),
    ("member@nawa.local", "Members"),
]

_POLICY_STATEMENTS: dict[str, list[dict]] = {
    "AdministratorAccess": [{"effect": "Allow", "actions": ["*"]}],
    "ProgramManagerAccess": [
        {
            "effect": "Allow",
            "actions": [
                "nawa:console:intake",
                "nawa:console:journey",
                "nawa:console:reports",
                "nawa:profiles:read",
                "nawa:programs:manage",
                "nawa:intake:*",
                "nawa:journey:*",
                "nawa:community:read",
                "nawa:community:match",
                "nawa:mentorship:manage",
                "nawa:reports:*",
                "nawa:audit:read",
            ],
        }
    ],
    "ReviewerAccess": [
        {
            "effect": "Allow",
            "actions": [
                "nawa:console:intake",
                "nawa:profiles:read",
                "nawa:intake:review",
                "nawa:intake:override",
            ],
        }
    ],
    "FounderAccess": [
        {
            "effect": "Allow",
            "actions": [
                "nawa:profiles:write",
                "nawa:journey:read",
                "nawa:journey:assist",
                "nawa:community:read",
                "nawa:community:post",
                "nawa:kpi:write",
            ],
        }
    ],
    "MentorAccess": [
        {
            "effect": "Allow",
            "actions": [
                "nawa:profiles:read",
                "nawa:community:read",
                "nawa:community:post",
                "nawa:journey:assist",
            ],
        }
    ],
    "ModeratorAccess": [
        {
            "effect": "Allow",
            "actions": [
                "nawa:profiles:read",
                "nawa:community:read",
                "nawa:community:post",
                "nawa:community:moderate",
            ],
        }
    ],
    "MembersBaseline": [
        {"effect": "Allow", "actions": ["nawa:profiles:write", "nawa:community:read"]}
    ],
}

_GROUP_TO_POLICY = {
    "Administrators": "AdministratorAccess",
    "Program Managers": "ProgramManagerAccess",
    "Reviewers": "ReviewerAccess",
    "Founders": "FounderAccess",
    "Mentors": "MentorAccess",
    "Moderators": "ModeratorAccess",
    "Members": "MembersBaseline",
}


@dataclass
class IamSeedResult:
    group_ids_by_name: dict[str, uuid.UUID] = field(default_factory=dict)
    user_ids_by_identifier: dict[str, uuid.UUID] = field(default_factory=dict)
    members_group_id: uuid.UUID | None = None

    def user_id(self, identifier: str) -> uuid.UUID:
        return self.user_ids_by_identifier[identifier]

    def group_id(self, name: str) -> uuid.UUID:
        return self.group_ids_by_name[name]


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=4)).decode("utf-8")


async def seed_iam(session: AsyncSession) -> IamSeedResult:
    result = IamSeedResult()

    policy_ids_by_name: dict[str, uuid.UUID] = {}
    for policy_name, statements in _POLICY_STATEMENTS.items():
        policy = await create_policy_db(
            name=policy_name, statements=statements, managed=True, session=session
        )
        policy_ids_by_name[policy_name] = policy.id

    for group_name, policy_name in _GROUP_TO_POLICY.items():
        group = await create_group_db(
            name=group_name,
            policy_ids=[policy_ids_by_name[policy_name]],
            managed=True,
            session=session,
        )
        result.group_ids_by_name[group_name] = group.id

    result.members_group_id = result.group_ids_by_name["Members"]

    password_hash = _hash_password("password")
    for identifier, group_name in CREDENTIALS_TABLE:
        username = identifier.split("@")[0]
        user = await create_user_db(
            email=identifier,
            username=username,
            password_hash=password_hash,
            full_name=username.capitalize(),
            session=session,
        )
        result.user_ids_by_identifier[identifier] = user.id

        # Every seeded user is a member of Members, mirroring signup (§8.1).
        target_group_id = result.group_ids_by_name[group_name]
        await add_group_member_db(group_id=target_group_id, user_id=user.id, session=session)
        if group_name != "Members":
            await add_group_member_db(
                group_id=result.members_group_id, user_id=user.id, session=session
            )

    return result
