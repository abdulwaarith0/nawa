"use client";

import { Alert, Button, Input, Textarea } from "@/components";
import { useT } from "@/i18n/useT";
import { getApiClient } from "@/lib/apiClient";
import { Routes } from "@nawa/contracts";
import { Building2, CheckCircle2, Mail, MessageSquareText, User } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type FieldErrors = {
  fullName?: string;
  email?: string;
  organization?: string;
  reason?: string;
};

// Request-access feature wrapper (design-qa-request-access.md, ported into
// AuthShell's split panel): admin-reviewed, not self-serve — submitting does
// NOT sign the applicant in. It creates a pending request; an admin approves
// or rejects it from /admin/access-requests, and approval triggers the
// existing password-reset mechanism so the applicant can set a password.
export default function RequestAccessWrapper() {
  const t = useT("auth");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [organization, setOrganization] = useState("");
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const onSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError(null);

      const nextErrors: FieldErrors = {};
      if (!fullName.trim()) nextErrors.fullName = t("requestAccess.nameError");
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
        nextErrors.email = t("requestAccess.emailError");
      if (!organization.trim()) nextErrors.organization = t("requestAccess.organizationError");
      if (!reason.trim()) nextErrors.reason = t("requestAccess.reasonError");
      setErrors(nextErrors);
      if (Object.keys(nextErrors).length > 0) return;

      setSubmitting(true);
      try {
        await getApiClient().auth.requestAccess({
          full_name: fullName,
          email,
          organization,
          reason,
        });
        setSubmitted(true);
      } catch {
        setError(t("requestAccess.error"));
      } finally {
        setSubmitting(false);
      }
    },
    [fullName, email, organization, reason, t],
  );

  useEffect(() => {
    if (!error) return;
    const timer = window.setTimeout(() => setError(null), 6000);
    return () => window.clearTimeout(timer);
  }, [error]);

  return useMemo(() => {
    if (submitted) {
      return (
        <div className="nw-auth-confirmation" role="status" aria-live="polite">
          <div className="nw-auth-emblem nw-auth-emblem--success" aria-hidden="true">
            <CheckCircle2 size={26} />
          </div>
          <p className="nw-auth-kicker">{t("requestAccess.confirmationKicker")}</p>
          <h1>
            {t("requestAccess.confirmationTitle", {
              name: fullName.trim().split(" ")[0] ?? fullName,
            })}
          </h1>
          <p className="nw-auth-confirmation-body">
            {t("requestAccess.confirmationBody", { organization, email })}
          </p>
          <Link className="nw-btn nw-btn-secondary nw-auth-submit" href={Routes.login}>
            {t("requestAccess.backToSignIn")}
          </Link>
        </div>
      );
    }

    return (
      <>
        <div className="nw-auth-intro">
          <div className="nw-auth-emblem" aria-hidden="true">
            <img src="/brand/nawa-emblem.svg" alt="" />
          </div>
          <p className="nw-auth-kicker">Nawa Console</p>
          <h1>{t("requestAccess.title")}</h1>
          <p>{t("requestAccess.subtitle")}</p>
        </div>

        {error ? <Alert severity="danger">{error}</Alert> : null}

        <form className="nw-auth-form" onSubmit={onSubmit} noValidate>
          <div className="nw-auth-field">
            <label htmlFor="ra-name">{t("requestAccess.fullNameLabel")}</label>
            <div className="nw-auth-input-wrap">
              <User size={17} aria-hidden="true" />
              <Input
                id="ra-name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
                dirAuto
                error={errors.fullName}
              />
            </div>
          </div>

          <div className="nw-auth-field">
            <label htmlFor="ra-email">{t("requestAccess.emailLabel")}</label>
            <div className="nw-auth-input-wrap">
              <Mail size={17} aria-hidden="true" />
              <Input
                id="ra-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                error={errors.email}
              />
            </div>
          </div>

          <div className="nw-auth-field">
            <label htmlFor="ra-organization">{t("requestAccess.organizationLabel")}</label>
            <div className="nw-auth-input-wrap">
              <Building2 size={17} aria-hidden="true" />
              <Input
                id="ra-organization"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                autoComplete="organization"
                dirAuto
                error={errors.organization}
              />
            </div>
          </div>

          <div className="nw-auth-field">
            <label htmlFor="ra-reason">{t("requestAccess.reasonLabel")}</label>
            <div className="nw-auth-input-wrap nw-auth-input-wrap--textarea">
              <MessageSquareText size={17} aria-hidden="true" />
              <Textarea
                id="ra-reason"
                rows={3}
                placeholder={t("requestAccess.reasonPlaceholder")}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                error={errors.reason}
                dir="auto"
              />
            </div>
          </div>

          <Button type="submit" loading={submitting} className="nw-auth-submit">
            {t("requestAccess.submit")}
          </Button>
        </form>

        <p className="nw-auth-access">
          {t("requestAccess.haveAccount")}{" "}
          <Link href={Routes.login}>{t("requestAccess.signIn")}</Link>
        </p>

        <p className="nw-auth-legal">
          By continuing, you agree to Nawa&rsquo;s <a href="#terms">Terms</a> and{" "}
          <a href="#privacy">Privacy Policy</a>.
        </p>
      </>
    );
  }, [submitted, t, fullName, email, organization, reason, errors, error, submitting, onSubmit]);
}
