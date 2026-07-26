"use client";

import {
  Avatar,
  Badge,
  Card,
  Checkbox,
  EmptyState,
  ErrorState,
  Input,
  Loading,
  Select,
} from "@/components";
import type { DirectoryMember } from "@/hooks/Community";
import { useDirectory } from "@/hooks/Community";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { Routes } from "@nawa/contracts";
import Link from "next/link";
import { useEffect, useState } from "react";
import "./styles.css";

const STAGES = ["idea", "prototype", "pilot", "revenue", "growth"] as const;
const DEBOUNCE_MS = 300;

function MemberCard({ member }: { member: DirectoryMember }) {
  const t = useT("community");
  const locale = useLocale();
  const name = (locale === "ar" ? member.display_name_ar : member.display_name_en) ?? member.handle;
  const venture = locale === "ar" ? member.venture_name_ar : member.venture_name_en;

  return (
    <Link href={Routes.profile(member.handle)} className="nw-community-card-link">
      <Card className="nw-community-card">
        <div className="nw-community-card-head">
          <Avatar name={name} size={44} />
          <div>
            <bdi dir="auto" className="nw-community-card-name">
              {name}
            </bdi>
            {venture ? (
              <bdi dir="auto" className="nw-community-card-venture">
                {venture}
              </bdi>
            ) : null}
          </div>
        </div>
        <div className="nw-community-card-badges">
          <Badge tone="neutral">{t(`stage.${member.stage}`)}</Badge>
          {member.is_mentor_eligible ? <Badge tone="success">{t("mentorBadge")}</Badge> : null}
        </div>
        {member.skills.length > 0 ? (
          <div className="nw-community-card-badges">
            {member.skills.slice(0, 4).map((skill) => (
              <Badge key={skill} tone="neutral">
                {skill}
              </Badge>
            ))}
          </div>
        ) : null}
      </Card>
    </Link>
  );
}

// Member directory (08-community-hub.md §3, `/community`). Honestly drops
// the mock's requests-desk rail, AI match card, and "post request" composer
// — deliverable C (the requests desk) has no backend yet.
export default function CommunityWrapper() {
  const t = useT("community");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [stage, setStage] = useState("");
  const [mentorsOnly, setMentorsOnly] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  const { members, error, isLoading } = useDirectory({
    q: debouncedQuery || undefined,
    stage: stage || undefined,
    mentors: mentorsOnly || undefined,
  });

  let body: React.ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error) {
    body = <ErrorState onRetry={() => window.location.reload()} />;
  } else if (!members || members.length === 0) {
    body = <EmptyState headline={t("empty")} />;
  } else {
    body = (
      <div className="nw-three-grid">
        {members.map((member) => (
          <MemberCard key={member.id} member={member} />
        ))}
      </div>
    );
  }

  return (
    <ConsoleShell>
      <div className="nw-shell">
        <div className="nw-page-head">
          <div>
            <div className="nw-page-eyebrow">{t("eyebrow")}</div>
            <h1 className="nw-page-title">{t("title")}</h1>
          </div>
        </div>

        <Guard permission="nawa:community:read">
          <div className="nw-community-filters">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("searchPlaceholder")}
              aria-label={t("searchPlaceholder")}
              dirAuto
            />
            <Select
              aria-label={t("stageFilter")}
              value={stage}
              onChange={(e) => setStage(e.target.value)}
              options={[
                { value: "", label: t("stageFilter") },
                ...STAGES.map((s) => ({ value: s, label: t(`stage.${s}`) })),
              ]}
            />
            <Checkbox
              label={t("mentorsOnly")}
              checked={mentorsOnly}
              onChange={(e) => setMentorsOnly(e.target.checked)}
            />
          </div>
          {body}
        </Guard>
      </div>
    </ConsoleShell>
  );
}
