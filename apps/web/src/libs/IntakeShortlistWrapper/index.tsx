"use client";

import {
  AiAttribution,
  Badge,
  Button,
  Callout,
  Card,
  EmptyState,
  ErrorState,
  Input,
  Loading,
  Table,
  type TableColumn,
} from "@/components";
import { type ShortlistFilters, type ShortlistRow, useExport, useShortlist } from "@/hooks/Intake";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { getApiClient } from "@/lib/apiClient";
import { Routes } from "@nawa/contracts";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import "./styles.css";

const BAND_OPTIONS = ["", "0-40", "40-70", "70-100"];
const BULK_DECISIONS = ["shortlist", "waitlist", "reject"] as const;

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
// re-filtering of an already-filtered server page.
export default function IntakeShortlistWrapper({ cycleId }: IProps) {
  const t = useT("intake");
  const router = useRouter();
  const [filters, setFilters] = useState<ShortlistFilters>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkDecision, setBulkDecision] = useState<(typeof BULK_DECISIONS)[number] | "">("");
  const [bulkReason, setBulkReason] = useState("");
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [bulkPending, setBulkPending] = useState(false);

  const { rows, error, isLoading, refresh } = useShortlist(cycleId, filters);
  const exportShortlist = useExport(cycleId);

  function toggleFlag(flag: string) {
    setFilters((prev) => {
      const flags = new Set(prev.flags ?? []);
      if (flags.has(flag)) flags.delete(flag);
      else flags.add(flag);
      return { ...prev, flags: [...flags] };
    });
  }

  const toggleSelected = useCallback((applicationId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(applicationId)) next.delete(applicationId);
      else next.add(applicationId);
      return next;
    });
  }, []);

  async function applyBulkDecision() {
    if (!bulkDecision || selected.size === 0) return;
    setBulkPending(true);
    setBulkError(null);
    const failures: string[] = [];
    for (const applicationId of selected) {
      try {
        await getApiClient().post(`/intake/applications/${applicationId}/decision`, {
          decision: bulkDecision,
          reason: bulkReason.trim() || null,
        });
      } catch {
        failures.push(applicationId);
      }
    }
    setBulkPending(false);
    if (failures.length > 0) {
      setBulkError(`${failures.length} decision(s) failed — a reason may be required.`);
    } else {
      setSelected(new Set());
      setBulkDecision("");
      setBulkReason("");
    }
    refresh();
  }

  async function handleExport() {
    const result = await exportShortlist.run();
    window.open(result.url, "_blank", "noopener,noreferrer");
  }

  const columns: TableColumn<ShortlistRow>[] = useMemo(
    () => [
      {
        key: "select",
        header: "",
        render: (row) => (
          <input
            type="checkbox"
            checked={selected.has(row.application_id)}
            onChange={(event) => {
              event.stopPropagation();
              toggleSelected(row.application_id);
            }}
            onClick={(event) => event.stopPropagation()}
          />
        ),
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

  let body: React.ReactNode;
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
    <ConsoleShell title={t("shortlist.title")}>
      <Guard permission="nawa:console:intake">
        <p className="nw-intake-subtitle">{t("shortlist.subtitle")}</p>

        <Card className="nw-shortlist-filters">
          <select
            className="nw-select"
            value={filters.scoreBand ?? ""}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, scoreBand: event.target.value || undefined }))
            }
          >
            {BAND_OPTIONS.map((band) => (
              <option key={band} value={band}>
                {band || t("shortlist.filters.scoreBand")}
              </option>
            ))}
          </select>
          <Input
            placeholder={t("shortlist.filters.language")}
            value={filters.language ?? ""}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, language: event.target.value || undefined }))
            }
          />
          <Input
            placeholder={t("shortlist.filters.country")}
            value={filters.country ?? ""}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, country: event.target.value || undefined }))
            }
          />
          <Input
            placeholder={t("shortlist.filters.search")}
            value={filters.q ?? ""}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, q: event.target.value || undefined }))
            }
          />
          <label className="nw-shortlist-flag-check">
            <input
              type="checkbox"
              checked={(filters.flags ?? []).includes("hidden_gem")}
              onChange={() => toggleFlag("hidden_gem")}
            />
            {t("shortlist.filters.flags.hiddenGem")}
          </label>
          <label className="nw-shortlist-flag-check">
            <input
              type="checkbox"
              checked={(filters.flags ?? []).includes("dedup_pending")}
              onChange={() => toggleFlag("dedup_pending")}
            />
            {t("shortlist.filters.flags.dedupPending")}
          </label>
          <label className="nw-shortlist-flag-check">
            <input
              type="checkbox"
              checked={(filters.flags ?? []).includes("normalize_failed")}
              onChange={() => toggleFlag("normalize_failed")}
            />
            {t("shortlist.filters.flags.normalizeFailed")}
          </label>
          <Button variant="ghost" onClick={() => setFilters({})}>
            {t("shortlist.filters.clear")}
          </Button>
          <Button variant="secondary" onClick={handleExport} loading={exportShortlist.isPending}>
            {t("shortlist.export")}
          </Button>
        </Card>

        {selected.size > 0 ? (
          <Card className="nw-shortlist-bulk-bar">
            <select
              className="nw-select"
              value={bulkDecision}
              onChange={(event) =>
                setBulkDecision(event.target.value as (typeof BULK_DECISIONS)[number] | "")
              }
            >
              <option value="">{t("decision.title")}</option>
              {BULK_DECISIONS.map((choice) => (
                <option key={choice} value={choice}>
                  {t(`decision.actions.${choice}`)}
                </option>
              ))}
            </select>
            <Input
              placeholder={t("decision.reasonPlaceholder")}
              value={bulkReason}
              onChange={(event) => setBulkReason(event.target.value)}
              dirAuto
            />
            <Button onClick={applyBulkDecision} loading={bulkPending} disabled={!bulkDecision}>
              {t("decision.submit")} ({selected.size})
            </Button>
          </Card>
        ) : null}
        {bulkError ? <Callout tone="info">{bulkError}</Callout> : null}

        {body}
      </Guard>
    </ConsoleShell>
  );
}
