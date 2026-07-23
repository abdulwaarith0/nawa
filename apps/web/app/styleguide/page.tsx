"use client";

import { PERMISSION_META } from "@nawa/contracts";
import { useState } from "react";
import { AiAttribution } from "../../src/components/ai/AiAttribution";
import { Alert } from "../../src/components/ui/Alert";
import { Avatar } from "../../src/components/ui/Avatar";
import { Badge } from "../../src/components/ui/Badge";
import { Bidi } from "../../src/components/ui/Bidi";
import { Button } from "../../src/components/ui/Button";
import { Callout } from "../../src/components/ui/Callout";
import { Card } from "../../src/components/ui/Card";
import { Chip } from "../../src/components/ui/Chip";
import { Input } from "../../src/components/ui/Input";
import { Progress } from "../../src/components/ui/Progress";
import { StatTile } from "../../src/components/ui/StatTile";
import { EmptyState, ErrorState, Loading, Skeleton } from "../../src/components/ui/states";
import { LocaleProvider } from "../../src/i18n/LocaleProvider";

const TEAL = ["900", "700", "600", "500", "100", "50"];
const AMBER = ["800", "600", "500", "100", "50"];
const SAND = ["50", "100", "200"];
const SEMANTIC = ["success", "warning", "danger", "info"];

function Swatch({ token }: { token: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div
        style={{
          width: 64,
          height: 48,
          borderRadius: "var(--nw-radius-sm)",
          background: `var(${token})`,
          border: "1px solid var(--nw-sand-200)",
        }}
      />
      <code style={{ fontSize: "var(--nw-text-xs)", color: "var(--nw-ink-600)" }}>
        {token.replace("--nw-", "")}
      </code>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginTop: "var(--nw-space-8)" }}>
      <h2 className="nw-display" style={{ fontSize: "var(--nw-text-xl)" }}>
        {title}
      </h2>
      <div style={{ marginTop: "var(--nw-space-4)" }}>{children}</div>
    </section>
  );
}

const row = {
  display: "flex",
  gap: "var(--nw-space-3)",
  flexWrap: "wrap" as const,
  alignItems: "center",
};

export default function StyleguidePage() {
  const [locale, setLocale] = useState<"ar" | "en">("ar");
  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <LocaleProvider locale={locale}>
      <div
        lang={locale}
        dir={dir}
        style={{ padding: "var(--nw-space-8)", maxWidth: 980, marginInline: "auto" }}
      >
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h1 className="nw-display" style={{ fontSize: "var(--nw-text-3xl)" }}>
            NAWA Styleguide
          </h1>
          <Button variant="secondary" onClick={() => setLocale((l) => (l === "ar" ? "en" : "ar"))}>
            {locale === "ar" ? "English" : "العربية"}
          </Button>
        </header>

        <Section title="Palette">
          <div style={{ ...row, gap: "var(--nw-space-4)" }}>
            {TEAL.map((s) => (
              <Swatch key={s} token={`--nw-teal-${s}`} />
            ))}
            {AMBER.map((s) => (
              <Swatch key={s} token={`--nw-amber-${s}`} />
            ))}
            {SAND.map((s) => (
              <Swatch key={s} token={`--nw-sand-${s}`} />
            ))}
            {SEMANTIC.map((s) => (
              <Swatch key={s} token={`--nw-${s}-700`} />
            ))}
          </div>
        </Section>

        <Section title="Buttons">
          <div style={row}>
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Danger</Button>
            <Button loading>Loading</Button>
          </div>
        </Section>

        <Section title="Badges & Chips">
          <div style={row}>
            <Badge tone="success">Live</Badge>
            <Badge tone="warning">Stalled</Badge>
            <Badge tone="danger">Removed</Badge>
            <Badge tone="info">Draft</Badge>
            <Chip selected onSelect={() => {}}>
              robotics
            </Chip>
            <Chip onRemove={() => {}}>health-tech</Chip>
          </div>
        </Section>

        <Section title="Inputs">
          <div style={{ display: "grid", gap: "var(--nw-space-4)", maxWidth: 360 }}>
            <Input label="Email" hint="you@example.com" />
            <Input label="Handle" error="This handle is taken" defaultValue="ahmed" />
          </div>
        </Section>

        <Section title="Alerts & Callouts">
          <div style={{ display: "grid", gap: "var(--nw-space-3)" }}>
            <Alert severity="info" onDismiss={() => {}}>
              Informational banner.
            </Alert>
            <Alert severity="warning">Terracotta warning — never amber.</Alert>
            <Alert severity="danger">Human-confirmed danger state.</Alert>
            <Callout tone="success">A static success callout.</Callout>
          </div>
        </Section>

        <Section title="Stats, Progress & States">
          <div style={{ ...row, alignItems: "flex-start", gap: "var(--nw-space-8)" }}>
            <Card>
              <StatTile label="MRR" value={1200} unit="QAR" deltaPct={20} />
            </Card>
            <Card>
              <StatTile label="Churn" value={7} unit="%" deltaPct={-3} />
            </Card>
            <div style={{ minWidth: 200 }}>
              <Progress value={40} valueText="step 2 of 5" label="Onboarding" />
              <div style={{ marginTop: "var(--nw-space-3)" }}>
                <Skeleton width={180} />
              </div>
              <div style={{ marginTop: "var(--nw-space-3)" }}>
                <Loading />
              </div>
            </div>
          </div>
          <div
            style={{ marginTop: "var(--nw-space-4)", display: "grid", gap: "var(--nw-space-3)" }}
          >
            <Card>
              <EmptyState
                headline="No applications scored yet"
                description="Upload a batch to begin screening."
                action={<Button>Upload batch</Button>}
              />
            </Card>
            <ErrorState onRetry={() => {}} />
          </div>
        </Section>

        <Section title="AI attribution (amber = AI only)">
          <AiAttribution how={<p>Model class: LARGE · saw the applicant's own text only.</p>}>
            <p>
              This scorecard was drafted by the model. Every AI output carries the amber marker, a
              sparkle glyph, and the localized label.
            </p>
          </AiAttribution>
        </Section>

        <Section title="Bidi (mixed-direction names)">
          <p>
            Founder <Bidi>Ahmed Al-Sayed</Bidi> · venture <Bidi>QAR 1.2M</Bidi> ·{" "}
            <Avatar name="Ahmed Al-Sayed" />
          </p>
        </Section>

        <Section title="IAM vocabulary (generated from the Python catalog)">
          <p style={{ color: "var(--nw-ink-600)" }}>
            {Object.keys(PERMISSION_META).length} permissions in @nawa/contracts.
          </p>
        </Section>
      </div>
    </LocaleProvider>
  );
}
