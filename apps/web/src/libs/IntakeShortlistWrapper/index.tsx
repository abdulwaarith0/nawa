"use client";

import {
  AiAttribution,
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  EmptyState,
  ErrorState,
  Input,
  Loading,
  Select,
  Table,
  type TableColumn,
} from "@/components";
import { isDecidableStatus } from "@/helpers/intakeDecisions";
import { type ShortlistFilters, type ShortlistRow, useExport, useShortlist } from "@/hooks/Intake";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { getApiClient } from "@/lib/apiClient";
import { Routes } from "@nawa/contracts";
import { useRouter } from "next/navigation";
import { type ReactNode, useCallback, useMemo, useState } from "react";
import "./styles.css";

const BAND_OPTIONS = ["", "0-40", "40-70", "70-100"];
const BULK_DECISIONS = ["shortlist", "waitlist", "reject"] as const;
const MIN_REASON_LENGTH = 20;
const PAGE_SIZE = 25;
// "decided" is deliberately excluded: the API's own `_VALID_DECISIONS` set
// (list_shortlist.py) doesn't recognize it as a filter value — passing it
// silently resets the filter to "no filter" server-side, so it would be a
// dead tab that looks like it does something but doesn't.
const DECISION_STATES = ["shortlist", "waitlist", "reject", "accept", "undecided"] as const;

function decisionTone(
  decision: ShortlistRow["decision"],
): "neutral" | "success" | "warning" | "danger" | "info" {
  switch (decision) {
    case "shortlist":
      return "info";
    case "waitlist":
      return "warning";
    case "reject":
      return "danger";
    case "accept":
      return "success";
    default:
      return "neutral";
  }
}

export interface IProps {
  cycleId: string;
}

// Ranked shortlist view (design-system §6.3.2, `/intake/cycles/[id]`). Every
// filter maps 1:1 onto the API's own query params — no client-side
// re-filtering of an already-filtered server page. Bulk decisions gate a
// reason on the two negative outcomes (waitlist/reject), matching the
// human-override safety pattern already used by the scorecard's DecisionPanel.
export default function IntakeShortlistWrapper({ cycleId }: IProps) {
  const t = useT("intake");
  const router = useRouter();
  const [baseFilters, setBaseFilters] = useState<Omit<ShortlistFilters, "limit" | "offset">>({});
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkDecision, setBulkDecision] = useState<(typeof BULK_DECISIONS)[number] | "">("");
  const [bulkReason, setBulkReason] = useState("");
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [bulkPending, setBulkPending] = useState(false);

  const filters = useMemo<ShortlistFilters>(
    () => ({ ...baseFilters, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    [baseFilters, page],
  );
  const { rows, error, isLoading, refresh } = useShortlist(cycleId, filters);
  const exportShortlist = useExport(cycleId);

  const updateFilters = useCallback((patch: Partial<ShortlistFilters>) => {
    setPage(0);
    setBaseFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  const clearFilters = useCallback(() => {
    setPage(0);
    setBaseFilters({});
  }, []);

  const toggleFlag = useCallback(
    (flag: string) => {
      const flags = new Set(baseFilters.flags ?? []);
      if (flags.has(flag)) flags.delete(flag);
      else flags.add(flag);
      updateFilters({ flags: [...flags] });
    },
    [baseFilters.flags, updateFilters],
  );

  const toggleSelected = useCallback((applicationId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(applicationId)) next.delete(applicationId);
      else next.add(applicationId);
      return next;
    });
  }, []);

  // The API requires a reason whenever a human decision diverges from the AI
  // band (decide_application.py) — the shortlist view has no per-row AI band
  // to predict that client-side, so a reason is always required for any bulk
  // decision rather than guessing which ones need it.
  const reasonTooShort = bulkDecision !== "" && bulkReason.trim().length < MIN_REASON_LENGTH;
  const canSubmitBulk = bulkDecision !== "" && selected.size > 0 && !reasonTooShort;

  const applyBulkDecision = useCallback(async () => {
    if (!canSubmitBulk || !bulkDecision) return;
    setBulkPending(true);
    setBulkError(null);
    let failureCount = 0;
    let lastMessage: string | null = null;
    for (const applicationId of selected) {
      try {
        await getApiClient().post(`/intake/applications/${applicationId}/decision`, {
          decision: bulkDecision,
          reason: bulkReason.trim(),
        });
      } catch (err) {
        failureCount += 1;
        lastMessage = err instanceof Error ? err.message : null;
      }
    }
    setBulkPending(false);
    if (failureCount > 0) {
      setBulkError(
        lastMessage
          ? t("shortlist.bulk.someFailedWithReason", { count: failureCount, message: lastMessage })
          : t("shortlist.bulk.someFailed", { count: failureCount }),
      );
    } else {
      setSelected(new Set());
      setBulkDecision("");
      setBulkReason("");
    }
    refresh();
  }, [canSubmitBulk, bulkDecision, selected, bulkReason, refresh, t]);

  const handleExport = useCallback(async () => {
    const result = await exportShortlist.run();
    window.open(result.url, "_blank", "noopener,noreferrer");
  }, [exportShortlist]);

  const columns: TableColumn<ShortlistRow>[] = useMemo(
    () => [
      {
        key: "select",
        header: "",
        render: (row) => {
          const decidable = isDecidableStatus(row.status);
          return (
            <Checkbox
              checked={selected.has(row.application_id)}
              disabled={!decidable}
              title={decidable ? undefined : t("shortlist.notScoredYet")}
              onChange={(event) => {
                event.stopPropagation();
                toggleSelected(row.application_id);
              }}
              onClick={(event) => event.stopPropagation()}
              aria-label={row.applicant_name}
            />
          );
        },
      },
      { key: "rank", header: t("shortlist.columns.rank"), render: (row) => row.rank, align: "end" },
      {
        key: "applicant",
        header: t("shortlist.columns.applicant"),
        render: (row) => <bdi dir="auto">{row.applicant_name}</bdi>,
      },
      {
        key: "title",
        header: t("shortlist.columns.title"),
        render: (row) => <bdi dir="auto">{row.title ?? "—"}</bdi>,
      },
      { key: "language", header: t("shortlist.columns.language"), render: (row) => row.language },
      {
        key: "country",
        header: t("shortlist.columns.country"),
        render: (row) => row.country ?? "—",
      },
      {
        key: "score",
        header: t("shortlist.columns.score"),
        align: "end",
        render: (row) =>
          row.total_score != null ? (
            <AiAttribution compact>{row.total_score.toFixed(1)}</AiAttribution>
          ) : (
            "—"
          ),
      },
      {
        key: "flags",
        header: "",
        render: (row) => (
          <span className="nw-shortlist-flags">
            {row.hidden_gem ? (
              <AiAttribution compact>{t("shortlist.filters.flags.hiddenGem")}</AiAttribution>
            ) : null}
            {row.dedup_pending ? (
              <AiAttribution compact>{t("shortlist.filters.flags.dedupPending")}</AiAttribution>
            ) : null}
          </span>
        ),
      },
      {
        key: "decision",
        header: t("shortlist.columns.decision"),
        render: (row) => (
          <Badge tone={decisionTone(row.decision)}>
            {t(`shortlist.decisionStates.${row.decision}`)}
          </Badge>
        ),
      },
    ],
    [t, selected, toggleSelected],
  );

  let body: ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error) {
    body = <ErrorState onRetry={() => refresh()} />;
  } else if (!rows || rows.length === 0) {
    body = <EmptyState headline={t("shortlist.empty")} />;
  } else {
    body = (
      <Table
        columns={columns}
        rows={rows}
        getRowKey={(row) => row.application_id}
        onRowClick={(row) => router.push(Routes.intake.application(row.application_id))}
      />
    );
  }

  return (
    <ConsoleShell>
      <div className="nw-shell">
        <div className="nw-page-head">
          <div>
            <div className="nw-page-eyebrow">{t("shortlist.eyebrow")}</div>
            <h1 className="nw-page-title">{t("shortlist.title")}</h1>
            <p className="nw-page-sub">{t("shortlist.subtitle")}</p>
          </div>
          <div className="nw-page-actions">
            <Button variant="ghost" onClick={clearFilters}>
              {t("shortlist.filters.clear")}
            </Button>
            <Button variant="secondary" onClick={handleExport} loading={exportShortlist.isPending}>
              {t("shortlist.export")}
            </Button>
          </div>
        </div>

        <Guard permission="nawa:console:intake">
          <div
            className="nw-shortlist-tabs"
            role="tablist"
            aria-label={t("shortlist.filters.decision")}
          >
            <button
              type="button"
              role="tab"
              aria-selected={!baseFilters.decision}
              data-active={!baseFilters.decision}
              className="nw-shortlist-tab"
              onClick={() => updateFilters({ decision: undefined })}
            >
              {t("shortlist.filters.anyDecision")}
            </button>
            {DECISION_STATES.map((state) => (
              <button
                key={state}
                type="button"
                role="tab"
                aria-selected={baseFilters.decision === state}
                data-active={baseFilters.decision === state}
                className="nw-shortlist-tab"
                onClick={() => updateFilters({ decision: state })}
              >
                {t(`shortlist.decisionStates.${state}`)}
              </button>
            ))}
          </div>

          <Card className="nw-shortlist-filters">
            <Select
              aria-label={t("shortlist.filters.scoreBand")}
              value={baseFilters.scoreBand ?? ""}
              onChange={(event) => updateFilters({ scoreBand: event.target.value || undefined })}
              options={BAND_OPTIONS.map((band) => ({
                value: band,
                label: band || t("shortlist.filters.scoreBand"),
              }))}
            />
            <Select
              aria-label={t("shortlist.filters.language")}
              value={baseFilters.language ?? ""}
              onChange={(event) => updateFilters({ language: event.target.value || undefined })}
              options={[
                { value: "", label: t("shortlist.filters.anyLanguage") },
                { value: "en", label: t("shortlist.filters.languageEn") },
                { value: "ar", label: t("shortlist.filters.languageAr") },
              ]}
            />
            <Input
              placeholder={t("shortlist.filters.country")}
              value={baseFilters.country ?? ""}
              onChange={(event) => updateFilters({ country: event.target.value || undefined })}
            />
            <Input
              placeholder={t("shortlist.filters.search")}
              value={baseFilters.q ?? ""}
              onChange={(event) => updateFilters({ q: event.target.value || undefined })}
            />
            <Checkbox
              checked={(baseFilters.flags ?? []).includes("hidden_gem")}
              onChange={() => toggleFlag("hidden_gem")}
              label={t("shortlist.filters.flags.hiddenGem")}
            />
            <Checkbox
              checked={(baseFilters.flags ?? []).includes("dedup_pending")}
              onChange={() => toggleFlag("dedup_pending")}
              label={t("shortlist.filters.flags.dedupPending")}
            />
            <Checkbox
              checked={(baseFilters.flags ?? []).includes("normalize_failed")}
              onChange={() => toggleFlag("normalize_failed")}
              label={t("shortlist.filters.flags.normalizeFailed")}
            />
          </Card>

          {body}

          {rows && rows.length > 0 ? (
            <div className="nw-shortlist-pagination">
              <Button
                variant="ghost"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                {t("shortlist.pagination.prev")}
              </Button>
              <span className="nw-shortlist-pagination-label">
                {t("shortlist.pagination.range", {
                  start: page * PAGE_SIZE + 1,
                  end: page * PAGE_SIZE + rows.length,
                })}
              </span>
              <Button
                variant="ghost"
                disabled={rows.length < PAGE_SIZE}
                onClick={() => setPage((p) => p + 1)}
              >
                {t("shortlist.pagination.next")}
              </Button>
            </div>
          ) : null}

          {bulkError ? <Alert severity="danger">{bulkError}</Alert> : null}

          {selected.size > 0 ? (
            <div className="nw-shortlist-bulk-bar">
              <span className="nw-shortlist-bulk-count">
                {t("shortlist.bulk.selected", { count: selected.size })}
              </span>
              <Select
                aria-label={t("decision.title")}
                value={bulkDecision}
                onChange={(event) =>
                  setBulkDecision(event.target.value as (typeof BULK_DECISIONS)[number] | "")
                }
                options={[
                  { value: "", label: t("decision.title") },
                  ...BULK_DECISIONS.map((choice) => ({
                    value: choice,
                    label: t(`decision.actions.${choice}`),
                  })),
                ]}
              />
              <Input
                placeholder={t("decision.reasonPlaceholder")}
                value={bulkReason}
                onChange={(event) => setBulkReason(event.target.value)}
                error={
                  reasonTooShort
                    ? t("shortlist.bulk.reasonTooShort", { min: MIN_REASON_LENGTH })
                    : undefined
                }
                dirAuto
              />
              <Button onClick={applyBulkDecision} loading={bulkPending} disabled={!canSubmitBulk}>
                {t("decision.submit")}
              </Button>
            </div>
          ) : null}
        </Guard>
      </div>
    </ConsoleShell>
  );
}
