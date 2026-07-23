"""Sentinel errors — frozen constants raised from anywhere in the stack.

One global exception handler (registered in the app factory) maps every
ApiError to the response envelope. The AI family (ERR_AI_*) is owned and
extended by 05-ai-infrastructure.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiError(Exception):
    code: int
    message: str


ERR_INVALID_FIELDS = ApiError(400, "Invalid fields")
ERR_UNAUTHENTICATED = ApiError(401, "Authentication required")
ERR_UNAUTHORIZED = ApiError(403, "You do not have permission to perform this action")
ERR_NOT_FOUND = ApiError(404, "Not found")
ERR_CONFLICT = ApiError(409, "Conflict")
ERR_RATE_LIMITED = ApiError(429, "Too many requests")
ERR_INTERNAL = ApiError(500, "Internal server error")
ERR_EMAIL_NOT_CONFIGURED = ApiError(503, "Email delivery is not configured")
ERR_SMS_NOT_CONFIGURED = ApiError(503, "SMS delivery is not configured")
ERR_STORAGE_NOT_CONFIGURED = ApiError(503, "Object storage is not configured")

# ERR_AI_* family — owned and extended by 05-ai-infrastructure.md
ERR_AI_NOT_CONFIGURED = ApiError(503, "The AI provider is not configured")
ERR_AI_BUDGET_EXCEEDED = ApiError(429, "The AI usage budget is exceeded")
ERR_AI_UNAVAILABLE = ApiError(503, "The AI provider is temporarily unavailable")
