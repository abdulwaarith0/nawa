"use client";

import { Alert, Button, Input } from "@/components";
import { nextTarget } from "@/helpers/nextTarget";
import { useT } from "@/i18n/useT";
import { getApiClient } from "@/lib/apiClient";
import { Routes } from "@nawa/contracts";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

// The login feature wrapper (design-qa.md — ported into AuthShell's split
// panel): owns form state + the api-client call. Content-sniffed identifier
// behavior is unchanged from before — only the "Work email" label and layout
// are new; the backend still accepts email, username, or phone.
export default function LoginWrapper() {
  const t = useT("auth");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError(null);
      setSubmitting(true);
      try {
        const result = (await getApiClient().auth.login(identifier, password)) as {
          effective?: string[];
        };
        // Full navigation so the server sees the fresh nw_session cookie.
        window.location.assign(nextTarget(result.effective));
      } catch {
        // Login errors are deliberately generic (non-enumerable, per the API).
        setError(t("login.error"));
        setSubmitting(false);
      }
    },
    [identifier, password, t],
  );

  const togglePassword = useCallback(() => setShowPassword((v) => !v), []);

  // Errors are transient feedback, not a permanent page state — clear them
  // automatically so a stale "wrong password" message doesn't linger after
  // the user has moved on.
  useEffect(() => {
    if (!error) return;
    const timer = window.setTimeout(() => setError(null), 6000);
    return () => window.clearTimeout(timer);
  }, [error]);

  return useMemo(
    () => (
      <>
        <div className="nw-auth-intro">
          <div className="nw-auth-emblem" aria-hidden="true">
            <img src="/brand/nawa-emblem.svg" alt="" />
          </div>
          <p className="nw-auth-kicker">Nawa Console</p>
          <h1>{t("login.title")}</h1>
          <p>{t("login.subtitle")}</p>
        </div>

        {error ? <Alert severity="danger">{error}</Alert> : null}

        <form className="nw-auth-form" onSubmit={onSubmit} noValidate>
          <div className="nw-auth-field">
            <label htmlFor="login-identifier">{t("login.identifierLabel")}</label>
            <div className="nw-auth-input-wrap">
              <Mail size={17} aria-hidden="true" />
              <Input
                id="login-identifier"
                placeholder={t("login.identifierPlaceholder")}
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                autoComplete="username"
                dirAuto
              />
            </div>
          </div>

          <div className="nw-auth-field">
            <div className="nw-auth-label-row">
              <label htmlFor="login-password">{t("login.passwordLabel")}</label>
              <button type="button" disabled title="Coming soon">
                {t("login.forgotPassword")}
              </button>
            </div>
            <div className="nw-auth-input-wrap nw-auth-password">
              <Lock size={17} aria-hidden="true" />
              <Input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button
                type="button"
                className="nw-auth-password-toggle"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                onClick={togglePassword}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            <span className="nw-auth-hint">{t("login.passwordHint")}</span>
          </div>

          <Button type="submit" loading={submitting} className="nw-auth-submit">
            {t("login.submit")}
          </Button>
        </form>

        <p className="nw-auth-access">
          {t("login.noAccount")} <Link href={Routes.requestAccess}>{t("login.apply")}</Link>
        </p>

        <p className="nw-auth-legal">
          By continuing, you agree to Nawa&rsquo;s <a href="#terms">Terms</a> and{" "}
          <a href="#privacy">Privacy Policy</a>.
        </p>
      </>
    ),
    [t, error, identifier, password, showPassword, submitting, togglePassword, onSubmit],
  );
}
