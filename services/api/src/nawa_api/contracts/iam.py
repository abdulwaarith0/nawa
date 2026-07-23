"""IAM vocabulary — pure data + pure functions, no DB imports.

This is the security kernel. `compile_statements` is the authority every
`require_permission` call ultimately relies on: it unions all Allows then
subtracts every Deny — explicit Deny always wins, no ordering games.

Later slices extend PERMISSION_META here (never with ad-hoc strings). The
whole map is mirrored into packages/contracts/src/gen/iam.ts by codegen so
client, edge, and server share one vocabulary.
"""

import re


class Permission:
    """Grep-able named constants used verbatim in `require_permission(...)`."""

    # console-entry permissions (gate whole UI sections)
    CONSOLE_INTAKE = "nawa:console:intake"
    CONSOLE_JOURNEY = "nawa:console:journey"
    CONSOLE_REPORTS = "nawa:console:reports"
    CONSOLE_ADMIN = "nawa:console:admin"
    # feature permissions
    PROFILES_READ = "nawa:profiles:read"
    PROFILES_WRITE = "nawa:profiles:write"
    PROFILES_MANAGE = "nawa:profiles:manage"
    PROGRAMS_MANAGE = "nawa:programs:manage"
    INTAKE_INGEST = "nawa:intake:ingest"
    INTAKE_SCORE = "nawa:intake:score"
    INTAKE_REVIEW = "nawa:intake:review"
    INTAKE_OVERRIDE = "nawa:intake:override"
    INTAKE_EXPORT = "nawa:intake:export"
    INTAKE_RUBRIC_MANAGE = "nawa:intake:rubric_manage"
    JOURNEY_READ = "nawa:journey:read"
    JOURNEY_MANAGE = "nawa:journey:manage"
    JOURNEY_DIGESTS = "nawa:journey:digests"
    JOURNEY_ASSIST = "nawa:journey:assist"
    COMMUNITY_READ = "nawa:community:read"
    COMMUNITY_POST = "nawa:community:post"
    COMMUNITY_MODERATE = "nawa:community:moderate"
    COMMUNITY_MATCH = "nawa:community:match"
    MENTORSHIP_MANAGE = "nawa:mentorship:manage"
    KPI_WRITE = "nawa:kpi:write"
    REPORTS_READ = "nawa:reports:read"
    REPORTS_GENERATE = "nawa:reports:generate"
    AI_STREAM = "nawa:ai:stream"
    AI_EVAL_RUN = "nawa:ai:eval_run"
    ADMIN_AI_CALLS_READ = "nawa:admin:ai_calls_read"
    IAM_MANAGE = "nawa:iam:manage"
    AUDIT_READ = "nawa:audit:read"
    ADMIN_MANAGE = "nawa:admin:manage"


# permission -> {label, description, kind}
PERMISSION_META: dict[str, dict] = {
    Permission.CONSOLE_INTAKE: {
        "label": "Access the intake console",
        "description": "Enter the intake screening console.",
        "kind": "console",
    },
    Permission.CONSOLE_JOURNEY: {
        "label": "Access the journey console",
        "description": "Enter the journey console.",
        "kind": "console",
    },
    Permission.CONSOLE_REPORTS: {
        "label": "Access the reports console",
        "description": "Enter the reports console.",
        "kind": "console",
    },
    Permission.CONSOLE_ADMIN: {
        "label": "Access the admin console",
        "description": "Enter the admin console.",
        "kind": "console",
    },
    Permission.PROFILES_READ: {
        "label": "View member profiles beyond the public projection",
        "description": "Read non-public profile fields.",
        "kind": "feature",
    },
    Permission.PROFILES_WRITE: {
        "label": "Edit own founder profile",
        "description": "Edit your own profile.",
        "kind": "feature",
    },
    Permission.PROFILES_MANAGE: {
        "label": "Edit any profile",
        "description": "Edit any member's profile.",
        "kind": "feature",
    },
    Permission.PROGRAMS_MANAGE: {
        "label": "Configure programs, cycles, rubrics, milestones",
        "description": "Manage program configuration.",
        "kind": "feature",
    },
    Permission.INTAKE_INGEST: {
        "label": "Ingest application batches",
        "description": "Upload and ingest applications.",
        "kind": "feature",
    },
    Permission.INTAKE_SCORE: {
        "label": "Run or refresh AI scoring",
        "description": "Trigger AI scoring runs.",
        "kind": "feature",
    },
    Permission.INTAKE_REVIEW: {
        "label": "Review applications, scorecards, and shortlists",
        "description": "Review intake artifacts.",
        "kind": "feature",
    },
    Permission.INTAKE_OVERRIDE: {
        "label": "Override AI scores and shortlist ranks",
        "description": "Override AI recommendations.",
        "kind": "feature",
    },
    Permission.INTAKE_EXPORT: {
        "label": "Export shortlists and intake decisions",
        "description": "Export intake data.",
        "kind": "feature",
    },
    Permission.INTAKE_RUBRIC_MANAGE: {
        "label": "Create and edit scoring rubrics",
        "description": "Manage rubrics.",
        "kind": "feature",
    },
    Permission.JOURNEY_READ: {
        "label": "View cohort milestones",
        "description": "Read cohort milestones.",
        "kind": "feature",
    },
    Permission.JOURNEY_MANAGE: {
        "label": "Manage cohorts and milestones",
        "description": "Manage journey configuration.",
        "kind": "feature",
    },
    Permission.JOURNEY_DIGESTS: {
        "label": "Generate and view weekly digests",
        "description": "Manage digests.",
        "kind": "feature",
    },
    Permission.JOURNEY_ASSIST: {
        "label": "Use the RAG assistant",
        "description": "Use the journey assistant.",
        "kind": "feature",
    },
    Permission.COMMUNITY_READ: {
        "label": "Browse the directory, requests, opportunities",
        "description": "Read community surfaces.",
        "kind": "feature",
    },
    Permission.COMMUNITY_POST: {
        "label": "Post requests and opportunities",
        "description": "Create community posts.",
        "kind": "feature",
    },
    Permission.COMMUNITY_MODERATE: {
        "label": "Moderate community content",
        "description": "Moderate the community.",
        "kind": "feature",
    },
    Permission.COMMUNITY_MATCH: {
        "label": "View and administer AI match runs",
        "description": "Administer matching.",
        "kind": "feature",
    },
    Permission.MENTORSHIP_MANAGE: {
        "label": "Manage mentor matching",
        "description": "Manage mentorships.",
        "kind": "feature",
    },
    Permission.KPI_WRITE: {
        "label": "Submit KPI check-ins and update KPI entries",
        "description": "Write KPI data.",
        "kind": "feature",
    },
    Permission.REPORTS_READ: {
        "label": "View portfolio dashboards",
        "description": "Read reports/dashboards.",
        "kind": "feature",
    },
    Permission.REPORTS_GENERATE: {
        "label": "Generate reports and digests",
        "description": "Generate reports.",
        "kind": "feature",
    },
    Permission.AI_STREAM: {
        "label": "Stream AI assistant responses",
        "description": "Stream AI output.",
        "kind": "feature",
    },
    Permission.AI_EVAL_RUN: {
        "label": "Run AI evaluation suites",
        "description": "Run AI evals.",
        "kind": "feature",
    },
    Permission.ADMIN_AI_CALLS_READ: {
        "label": "Browse the AI-call ledger",
        "description": "Read the ai_calls ledger.",
        "kind": "feature",
    },
    Permission.IAM_MANAGE: {
        "label": "Administer policies, groups, and user access",
        "description": "Manage IAM.",
        "kind": "feature",
    },
    Permission.AUDIT_READ: {
        "label": "Browse the audit log",
        "description": "Read audit logs.",
        "kind": "feature",
    },
    Permission.ADMIN_MANAGE: {
        "label": "Edit site configuration",
        "description": "Manage site config.",
        "kind": "feature",
    },
}

CATALOG: frozenset[str] = frozenset(PERMISSION_META.keys())

_ACTION_RE = re.compile(r"^(\*|nawa:[a-z_]+:(\*|[a-z_]+))$")


def validate_action(action: str) -> bool:
    """A statement action is `*`, `nawa:<domain>:*`, or an exact catalog permission."""
    if action == "*":
        return True
    if not _ACTION_RE.match(action):
        return False
    if action.endswith(":*"):
        domain = action.split(":")[1]
        return any(p.split(":")[1] == domain for p in CATALOG)
    return action in CATALOG


def expand_actions(actions: list[str]) -> set[str]:
    """Resolve wildcards against the catalog. Raises ValueError on any invalid action."""
    resolved: set[str] = set()
    for action in actions:
        if not validate_action(action):
            raise ValueError(f"Invalid action: {action!r}")
        if action == "*":
            resolved |= set(CATALOG)
        elif action.endswith(":*"):
            domain = action.split(":")[1]
            resolved |= {p for p in CATALOG if p.split(":")[1] == domain}
        else:
            resolved.add(action)
    return resolved


def compile_statements(statements: list[dict]) -> set[str]:
    """Union every Allow expansion, then subtract every Deny expansion.
    Explicit Deny always wins."""
    allowed: set[str] = set()
    denied: set[str] = set()
    for statement in statements:
        effect = statement.get("effect")
        actions = statement.get("actions", [])
        if effect == "Allow":
            allowed |= expand_actions(actions)
        elif effect == "Deny":
            denied |= expand_actions(actions)
    return allowed - denied


def describe_action(action: str) -> str:
    if action == "*":
        return "Full access to everything, plus anything added to any area later."
    if action.endswith(":*"):
        domain = action.split(":")[1]
        return f"Every permission in the {domain} area, plus anything added to this area later."
    meta = PERMISSION_META.get(action)
    return meta["label"] if meta else action


# --- Builtins (seeded managed=True, idempotently upserted on every boot) ---

BUILTIN_POLICIES: dict[str, list[dict]] = {
    "AdministratorAccess": [{"effect": "Allow", "actions": ["*"]}],
    "ProgramManagerAccess": [
        {
            "effect": "Allow",
            "actions": [
                Permission.CONSOLE_INTAKE,
                Permission.CONSOLE_JOURNEY,
                Permission.CONSOLE_REPORTS,
                Permission.PROFILES_READ,
                Permission.PROGRAMS_MANAGE,
                "nawa:intake:*",
                "nawa:journey:*",
                Permission.COMMUNITY_READ,
                Permission.COMMUNITY_MATCH,
                Permission.MENTORSHIP_MANAGE,
                "nawa:reports:*",
                Permission.AUDIT_READ,
            ],
        }
    ],
    "ReviewerAccess": [
        {
            "effect": "Allow",
            "actions": [
                Permission.CONSOLE_INTAKE,
                Permission.PROFILES_READ,
                Permission.INTAKE_REVIEW,
                Permission.INTAKE_OVERRIDE,
            ],
        }
    ],
    "FounderAccess": [
        {
            "effect": "Allow",
            "actions": [
                Permission.PROFILES_WRITE,
                Permission.JOURNEY_READ,
                Permission.JOURNEY_ASSIST,
                Permission.COMMUNITY_READ,
                Permission.COMMUNITY_POST,
                Permission.KPI_WRITE,
            ],
        }
    ],
    "MentorAccess": [
        {
            "effect": "Allow",
            "actions": [
                Permission.PROFILES_READ,
                Permission.COMMUNITY_READ,
                Permission.COMMUNITY_POST,
                Permission.JOURNEY_ASSIST,
            ],
        }
    ],
    "ModeratorAccess": [
        {
            "effect": "Allow",
            "actions": [
                Permission.PROFILES_READ,
                Permission.COMMUNITY_READ,
                Permission.COMMUNITY_POST,
                Permission.COMMUNITY_MODERATE,
            ],
        }
    ],
    "MembersBaseline": [
        {"effect": "Allow", "actions": [Permission.PROFILES_WRITE, Permission.COMMUNITY_READ]}
    ],
}

# group name -> the single policy attached to it
BUILTIN_GROUPS: dict[str, str] = {
    "Administrators": "AdministratorAccess",
    "Program Managers": "ProgramManagerAccess",
    "Reviewers": "ReviewerAccess",
    "Founders": "FounderAccess",
    "Mentors": "MentorAccess",
    "Moderators": "ModeratorAccess",
    "Members": "MembersBaseline",
}

MEMBERS_GROUP_NAME = "Members"


def home_for_permissions(perms: list[str]) -> str:
    """First-match landing surface, priority order per architecture §15."""
    p = set(perms)
    if Permission.CONSOLE_ADMIN in p:
        return "/admin"
    if Permission.CONSOLE_INTAKE in p:
        return "/intake"
    if Permission.CONSOLE_REPORTS in p:
        return "/reports/portfolio"
    if Permission.CONSOLE_JOURNEY in p:
        return "/journey"
    if Permission.COMMUNITY_READ in p:
        return "/community"
    return "/onboarding"
