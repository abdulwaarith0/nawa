"use client";

import { Alert, Button, Input } from "@/components";
import { useT } from "@/i18n/useT";
import { getApiClient } from "@/lib/apiClient";
import { type FormEvent, useCallback, useMemo, useState } from "react";

function nextTarget(): string {
  if (typeof window === "undefined") return "/";
  const next = new URLSearchParams(window.location.search).get("next");
  // Only allow same-origin relative paths.
  return next?.startsWith("/") ? next : "/";
}

// The login feature wrapper (design-system §6/§8): owns form state + the
// api-client call, renders inside <AuthShell/>.
export default function LoginWrapper() {
  const t = useT("auth");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError(null);
      setSubmitting(true);
      try {
        await getApiClient().auth.login(identifier, password);
        // Full navigation so the server sees the fresh nw_session cookie.
        window.location.assign(nextTarget());
      } catch {
        // Login errors are deliberately generic (non-enumerable, per the API).
        setError(t("login.error"));
        setSubmitting(false);
      }
    },
    [identifier, password, t],
  );

  return useMemo(
    () => (
      <form className="nw-auth-form" onSubmit={onSubmit} noValidate>
        <h1 className="nw-display" style={{ fontSize: "var(--nw-text-2xl)" }}>
          {t("login.title")}
        </h1>
        {error ? <Alert severity="danger">{error}</Alert> : null}
        <Input
          label={t("login.identifierLabel")}
          placeholder={t("login.identifierPlaceholder")}
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          autoComplete="username"
          dirAuto
        />
        <Input
          label={t("login.passwordLabel")}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        <Button type="submit" loading={submitting} className="nw-auth-submit">
          {t("login.submit")}
        </Button>
      </form>
    ),
    [t, error, identifier, password, submitting, onSubmit],
  );
}
