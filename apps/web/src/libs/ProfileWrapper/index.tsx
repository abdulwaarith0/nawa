"use client";

import { Avatar, Badge, Card, EmptyState, ErrorState, Loading } from "@/components";
import { useProfile } from "@/hooks/Profiles";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import "./styles.css";

export interface IProps {
  handle: string;
}

// The living Founder Profile page (08-community-hub.md §2, `/profile/[handle]`).
// No visual mock exists for this page (Documents/Nawa's design reference never
// built one) — laid out with the same shared components/tokens the rest of
// the app uses, not against a pixel spec.
export default function ProfileWrapper({ handle }: IProps) {
  const t = useT("profile");
  const locale = useLocale();
  const { profile, error, isLoading } = useProfile(handle);

  if (isLoading) {
    return (
      <ConsoleShell>
        <Loading />
      </ConsoleShell>
    );
  }
  if (error) {
    return (
      <ConsoleShell>
        <ErrorState onRetry={() => window.location.reload()} />
      </ConsoleShell>
    );
  }
  if (!profile) {
    return (
      <ConsoleShell>
        <EmptyState headline={t("notFound")} />
      </ConsoleShell>
    );
  }

  const name =
    (locale === "ar" ? profile.display_name_ar : profile.display_name_en) ?? profile.handle;
  const headline = locale === "ar" ? profile.headline_ar : profile.headline_en;
  const bio = locale === "ar" ? profile.bio_ar : profile.bio_en;
  const ventureName = locale === "ar" ? profile.venture_name_ar : profile.venture_name_en;
  const ventureSummary = locale === "ar" ? profile.venture_summary_ar : profile.venture_summary_en;
  const activeAsks = profile.asks.filter((a) => a.active);
  const hasKpis = Object.keys(profile.kpi_snapshot).length > 0;

  return (
    <ConsoleShell>
      <Guard permission="nawa:community:read">
        <div className="nw-shell">
          <div className="nw-profile-header">
            <Avatar name={name} size={64} />
            <div>
              <bdi dir="auto" className="nw-profile-name">
                {name}
              </bdi>
              {headline ? (
                <bdi dir="auto" className="nw-profile-headline">
                  {headline}
                </bdi>
              ) : null}
              <div className="nw-profile-badges">
                <Badge tone="neutral">{t(`stage.${profile.stage}`)}</Badge>
                {profile.is_mentor_eligible ? (
                  <Badge tone="success">{t("mentorBadge")}</Badge>
                ) : null}
                {profile.sector ? <Badge tone="neutral">{profile.sector}</Badge> : null}
                {profile.country ? <Badge tone="neutral">{profile.country}</Badge> : null}
              </div>
            </div>
          </div>

          <div className="nw-split-wide nw-section-gap">
            <div className="nw-profile-main">
              {ventureName ? (
                <Card className="nw-profile-card">
                  <h3>{ventureName}</h3>
                  {ventureSummary ? <p>{ventureSummary}</p> : null}
                  {profile.website ? (
                    <a href={profile.website} target="_blank" rel="noreferrer">
                      {profile.website}
                    </a>
                  ) : null}
                </Card>
              ) : null}

              {bio ? (
                <Card className="nw-profile-card">
                  <h3>{t("about")}</h3>
                  <p>{bio}</p>
                </Card>
              ) : null}

              <Card className="nw-profile-card">
                <h3>{t("kpis")}</h3>
                {hasKpis ? (
                  <pre className="nw-profile-kpi-raw">
                    {JSON.stringify(profile.kpi_snapshot, null, 2)}
                  </pre>
                ) : (
                  <p className="nw-intake-subtitle">{t("kpisEmpty")}</p>
                )}
              </Card>

              <Card className="nw-profile-card">
                <h3>{t("programHistory")}</h3>
                {profile.program_history.length === 0 ? (
                  <p className="nw-intake-subtitle">{t("programHistoryEmpty")}</p>
                ) : (
                  <ul className="nw-profile-history-list">
                    {profile.program_history.map((entry) => (
                      <li key={entry.cohort_id}>
                        <span>
                          {locale === "ar" ? entry.program_name_ar : entry.program_name_en}
                          {" · "}
                          {locale === "ar" ? entry.cohort_name_ar : entry.cohort_name_en}
                        </span>
                        <Badge tone="neutral">{entry.role}</Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            <div className="nw-profile-rail">
              {profile.skills.length > 0 ? (
                <Card className="nw-profile-card">
                  <h3>{t("skills")}</h3>
                  <div className="nw-profile-chip-row">
                    {profile.skills.map((skill) => (
                      <Badge key={skill} tone="neutral">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </Card>
              ) : null}

              {profile.domains.length > 0 ? (
                <Card className="nw-profile-card">
                  <h3>{t("domains")}</h3>
                  <div className="nw-profile-chip-row">
                    {profile.domains.map((domain) => (
                      <Badge key={domain} tone="neutral">
                        {domain}
                      </Badge>
                    ))}
                  </div>
                </Card>
              ) : null}

              <Card className="nw-profile-card">
                <h3>{t("asks")}</h3>
                {activeAsks.length === 0 ? (
                  <p className="nw-intake-subtitle">{t("asksEmpty")}</p>
                ) : (
                  <ul className="nw-profile-asks-list">
                    {activeAsks.map((ask, i) => (
                      // Asks have no stable id in the jsonb shape — index key
                      // is fine since this list is never reordered client-side.
                      // biome-ignore lint/suspicious/noArrayIndexKey: no stable id in this jsonb shape
                      <li key={i}>{locale === "ar" ? ask.text_ar : ask.text_en}</li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>
          </div>
        </div>
      </Guard>
    </ConsoleShell>
  );
}
