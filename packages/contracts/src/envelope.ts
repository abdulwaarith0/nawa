// The response envelope every NAWA endpoint returns, and the error-code
// constants that mirror contracts/errors.py.

export interface Envelope<T = unknown> {
  code: number;
  message: string;
  data: T | null;
}

export const ERROR_CODES = {
  INVALID_FIELDS: 400,
  UNAUTHENTICATED: 401,
  UNAUTHORIZED: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  RATE_LIMITED: 429,
  INTERNAL: 500,
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];
