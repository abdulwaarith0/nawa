"use client";

import { Badge, Button, Callout, Input, Progress, Select } from "@/components";
import { usePermissions } from "@/hooks/Auth";
import {
  useCycles,
  useScoreProgress,
  useShortlist,
  useTriggerScore,
  useUpload,
  useUploadProgress,
} from "@/hooks/Intake";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { Routes } from "@nawa/contracts";
import { ArrowRight, Check, CheckCircle2, Sparkles, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type ChangeEvent, type DragEvent, useMemo, useState } from "react";
import "./styles.css";

type Target = "applicant_name" | "applicant_email" | "phone" | "country" | "question" | "skip";
type Step = "upload" | "mapping" | "scoring" | "done";

interface MappingRow {
  source: string;
  target: Target;
  questionKey: string;
}

const TARGETS: Target[] = [
  "applicant_name",
  "applicant_email",
  "phone",
  "country",
  "question",
  "skip",
];

// Target values are snake_case (they double as the API's column_map field
// names); the i18n JSON keys are camelCase — this maps between the two
// rather than assuming they're string-identical.
const TARGET_I18N_KEY: Record<Target, string> = {
  applicant_name: "applicantName",
  applicant_email: "applicantEmail",
  phone: "phone",
  country: "country",
  question: "questionKey",
  skip: "unmapped",
};

const STEPS: Step[] = ["upload", "mapping", "scoring", "done"];

function detectCsvHeaders(text: string): string[] {
  const firstLine = text.split(/\r?\n/, 1)[0] ?? "";
  return firstLine
    .split(",")
    .map((h) => h.trim())
    .filter(Boolean);
}

function buildColumnMap(rows: MappingRow[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const row of rows) {
    if (row.target === "skip") continue;
    map[row.source] = row.target === "question" ? row.questionKey || row.source : row.target;
  }
  return map;
}

// Batch upload flow (design-system §6.3.1, `/intake/upload`) — a real 4-step
// version of the approved stepper design (Upload → Map columns → Score →
// Done). The design's 5th step, a pre-score "Review dedup" pass, has no
// backend equivalent yet: dedup matches are only computed once an
// application is scored (they compare embeddings), so there is nothing real
// to review before scoring runs. Every other step is the same real upload/
// score/progress plumbing this page already had — only the shell changed.
export default function IntakeWrapper() {
  const t = useT("intake");
  const { cycles, isLoading: cyclesLoading } = useCycles();
  const { has } = usePermissions();
  const searchParams = useSearchParams();
  const queryCycleId = searchParams.get("cycle") ?? "";

  // Carried forward from the console's own featured cycle via a ?cycle=
  // URL param — the approved design's Upload page has no cycle picker at
  // all (it assumes a single fixed cycle context), so this page only shows
  // its own picker as a fallback: a direct visit with no param, or more than
  // one cycle to choose between.
  const [cycleIdOverride, setCycleIdOverride] = useState("");
  const onlyCycle = cycles && cycles.length === 1 ? cycles[0] : undefined;
  const cycleId = cycleIdOverride || queryCycleId || onlyCycle?.id || "";
  const setCycleId = setCycleIdOverride;
  const [file, setFile] = useState<File | null>(null);
  const [rows, setRows] = useState<MappingRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<{ upload_id: string; row_count: number } | null>(
    null,
  );
  const [scoringStarted, setScoringStarted] = useState(false);

  const upload = useUpload(cycleId);
  const triggerScore = useTriggerScore(cycleId);
  const uploadProgress = useUploadProgress(uploadResult?.upload_id ?? null);
  const scoreProgress = useScoreProgress(scoringStarted ? cycleId : null);

  const scoringDone =
    scoringStarted &&
    scoreProgress.total > 0 &&
    scoreProgress.done + scoreProgress.failed >= scoreProgress.total;
  const step: Step = !uploadResult
    ? file
      ? "mapping"
      : "upload"
    : !scoringDone
      ? "scoring"
      : "done";
  const stepIndex = STEPS.indexOf(step);

  const { rows: doneRows } = useShortlist(step === "done" ? cycleId : null, {});
  const doneStats = useMemo(() => {
    if (!doneRows) return null;
    const scored = doneRows.filter((r) => r.total_score !== null);
    const shortlisted = doneRows.filter((r) => r.decision === "shortlist").length;
    const avg =
      scored.length > 0
        ? scored.reduce((sum, r) => sum + (r.total_score ?? 0), 0) / scored.length
        : 0;
    return { scored: scored.length, shortlisted, avg };
  }, [doneRows]);

  const columnMap = useMemo(() => buildColumnMap(rows), [rows]);
  const mappedRequired =
    rows.some((r) => r.target === "applicant_name") &&
    rows.some((r) => r.target === "applicant_email");

  function handleFile(next: File | null) {
    setFile(next);
    setError(null);
    if (next?.name.toLowerCase().endsWith(".csv")) {
      next.text().then((text) => {
        const headers = detectCsvHeaders(text);
        setRows(headers.map((source) => ({ source, target: "skip" as Target, questionKey: "" })));
      });
    } else {
      setRows([]);
    }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    handleFile(event.dataTransfer.files[0] ?? null);
  }

  function onFileInput(event: ChangeEvent<HTMLInputElement>) {
    handleFile(event.target.files?.[0] ?? null);
  }

  function addRow() {
    setRows((prev) => [...prev, { source: "", target: "skip", questionKey: "" }]);
  }

  function updateRow(index: number, patch: Partial<MappingRow>) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function reset() {
    setFile(null);
    setRows([]);
    setError(null);
  }

  async function handleUpload() {
    setError(null);
    if (!cycleId) {
      setError(t("upload.errors.noCycle"));
      return;
    }
    if (!file) {
      setError(t("upload.errors.noFile"));
      return;
    }
    try {
      const result = await upload.run(file, columnMap);
      setUploadResult(result);
    } catch {
      setError(upload.error instanceof Error ? upload.error.message : String(upload.error));
    }
  }

  async function handleRunScoring() {
    setScoringStarted(true);
    await triggerScore.run();
  }

  const selectedCycle = (cycles ?? []).find((c) => c.id === cycleId);
  const cycleLabel = selectedCycle
    ? `${selectedCycle.program_name_en ?? selectedCycle.program_name_ar} · ${selectedCycle.name_en ?? selectedCycle.name_ar}`
    : null;

  return (
    <ConsoleShell>
      <div className="nw-shell">
        <div className="nw-page-head">
          <div>
            <div className="nw-page-eyebrow">{t("upload.eyebrow")}</div>
            <h1 className="nw-page-title">{t("upload.title")}</h1>
            <p className="nw-page-sub">{cycleLabel ?? t("upload.subtitle")}</p>
          </div>
          <div className="nw-page-actions">
            <Link href={Routes.intake.home} className="nw-btn nw-btn-secondary">
              {t("upload.cancel")}
            </Link>
          </div>
        </div>

        <Guard permission="nawa:console:intake">
          {!cycleId ? (
            <div className="nw-intake-cycle-gate">
              <label className="nw-label" htmlFor="intake-cycle-picker">
                {t("upload.cyclePicker.label")}
              </label>
              <Select
                id="intake-cycle-picker"
                value={cycleId}
                disabled={cyclesLoading}
                onChange={(event) => setCycleId(event.target.value)}
                options={[
                  { value: "", label: t("upload.cyclePicker.placeholder") },
                  ...(cycles ?? []).map((cycle) => ({
                    value: cycle.id,
                    label: `${cycle.program_name_en ?? cycle.program_name_ar} — ${cycle.name_en ?? cycle.name_ar}`,
                  })),
                ]}
              />
            </div>
          ) : (
            <>
              <div className="nw-intake-stepper">
                {STEPS.map((s, i) => {
                  const state = i < stepIndex ? "done" : i === stepIndex ? "current" : "upcoming";
                  return (
                    <div key={s} className="nw-intake-step" data-state={state}>
                      <span className="nw-intake-step-badge">
                        {state === "done" ? <Check size={13} /> : i + 1}
                      </span>
                      {t(`upload.steps.${s}`)}
                      {i < STEPS.length - 1 ? <span className="nw-intake-step-rule" /> : null}
                    </div>
                  );
                })}
              </div>

              {step === "upload" ? (
                <div className="nw-card nw-intake-step-card">
                  <div
                    role="button"
                    tabIndex={0}
                    aria-label={t("upload.dropzone.label")}
                    className="nw-intake-dropzone-v2"
                    data-error={Boolean(error)}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={onDrop}
                    onClick={() => document.getElementById("intake-file-input")?.click()}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        document.getElementById("intake-file-input")?.click();
                      }
                    }}
                  >
                    <div className="nw-intake-dropzone-icon">
                      <UploadCloud size={26} aria-hidden="true" />
                    </div>
                    <p className="nw-intake-dropzone-title">{t("upload.dropzone.label")}</p>
                    <p className="nw-intake-dropzone-hint">{t("upload.dropzone.formats")}</p>
                    <label className="nw-btn nw-btn-primary">
                      <UploadCloud size={15} aria-hidden="true" />
                      {t("upload.dropzone.chooseFile")}
                      <input
                        id="intake-file-input"
                        type="file"
                        accept=".csv,.xlsx,.json"
                        onChange={onFileInput}
                        className="nw-intake-file-input"
                      />
                    </label>
                    {error ? (
                      <p className="nw-intake-dropzone-error" role="alert">
                        {error}
                      </p>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {step === "mapping" ? (
                <div className="nw-card nw-intake-mapping-card">
                  <div className="nw-intake-mapping-head">
                    <h3>{t("upload.columnMap.title")}</h3>
                    <p className="nw-intake-subtitle">{t("upload.columnMap.subtitle")}</p>
                  </div>
                  <div className="nw-intake-mapping-body">
                    {rows.map((row, index) => (
                      <div className="nw-intake-map-row" key={`${row.source}-${index}`}>
                        <Input
                          aria-label={t("upload.columnMap.title")}
                          value={row.source}
                          onChange={(event) => updateRow(index, { source: event.target.value })}
                          placeholder="column"
                        />
                        <ArrowRight size={15} className="nw-intake-map-arrow" aria-hidden="true" />
                        <div className="nw-intake-map-target">
                          <Select
                            aria-label={t("upload.columnMap.title")}
                            value={row.target}
                            onChange={(event) =>
                              updateRow(index, { target: event.target.value as Target })
                            }
                            options={TARGETS.map((target) => ({
                              value: target,
                              label: t(`upload.columnMap.${TARGET_I18N_KEY[target]}`),
                            }))}
                          />
                          {row.target === "question" ? (
                            <Input
                              aria-label={t("upload.columnMap.questionKey")}
                              value={row.questionKey}
                              onChange={(event) =>
                                updateRow(index, { questionKey: event.target.value })
                              }
                              placeholder={t("upload.columnMap.questionKey")}
                            />
                          ) : null}
                          {row.target === "skip" ? (
                            <Badge tone="neutral">{t("upload.columnMap.notScored")}</Badge>
                          ) : null}
                        </div>
                      </div>
                    ))}
                    <Button variant="ghost" onClick={addRow}>
                      + {t("upload.columnMap.addRow")}
                    </Button>
                  </div>
                  {error ? <Callout tone="info">{error}</Callout> : null}
                  <div className="nw-intake-mapping-footer">
                    <span className="nw-intake-mapping-status" data-ready={mappedRequired}>
                      {mappedRequired ? (
                        <>
                          <CheckCircle2 size={14} aria-hidden="true" />{" "}
                          {t("upload.columnMap.ready")}
                        </>
                      ) : (
                        t("upload.columnMap.needsRequired")
                      )}
                    </span>
                    <div className="nw-intake-mapping-actions">
                      <Button variant="secondary" onClick={reset}>
                        {t("upload.back")}
                      </Button>
                      <Button
                        onClick={handleUpload}
                        loading={upload.isPending}
                        disabled={!mappedRequired}
                      >
                        {upload.isPending ? t("upload.submitting") : t("upload.submit")}
                      </Button>
                    </div>
                  </div>
                </div>
              ) : null}

              {step === "scoring" ? (
                <div className="nw-card nw-intake-step-card">
                  <p className="nw-intake-uploaded-summary">
                    {t("upload.uploadedSummary", { count: uploadResult?.row_count ?? 0 })}
                  </p>
                  <div className="nw-intake-progress-block">
                    <div className="nw-intake-progress-head">
                      <span>
                        {t("upload.progress.normalizing", {
                          done: uploadProgress.done,
                          total: uploadProgress.total,
                        })}
                      </span>
                      <b>
                        {uploadProgress.total > 0
                          ? Math.round((uploadProgress.done / uploadProgress.total) * 100)
                          : 0}
                        %
                      </b>
                    </div>
                    <Progress
                      value={uploadProgress.done + uploadProgress.failed}
                      max={uploadProgress.total || 1}
                      label={t("upload.progress.normalizing", {
                        done: uploadProgress.done,
                        total: uploadProgress.total,
                      })}
                      valueText={`${uploadProgress.done}/${uploadProgress.total}`}
                    />
                  </div>
                  {uploadProgress.stoppedReason ? (
                    <Callout tone="info">
                      {t("upload.progress.stopped", { reason: uploadProgress.stoppedReason })}
                    </Callout>
                  ) : null}

                  {has("nawa:intake:score") ? (
                    scoringStarted ? (
                      <div className="nw-intake-progress-block">
                        <div className="nw-intake-progress-head">
                          <span>
                            {t("upload.progress.scoring", {
                              done: scoreProgress.done,
                              total: scoreProgress.total,
                            })}
                          </span>
                          <b>
                            {scoreProgress.total > 0
                              ? Math.round((scoreProgress.done / scoreProgress.total) * 100)
                              : 0}
                            %
                          </b>
                        </div>
                        <Progress
                          value={scoreProgress.done + scoreProgress.failed}
                          max={scoreProgress.total || 1}
                          label={t("upload.progress.scoring", {
                            done: scoreProgress.done,
                            total: scoreProgress.total,
                          })}
                          valueText={`${scoreProgress.done}/${scoreProgress.total}`}
                        />
                      </div>
                    ) : (
                      <Button onClick={handleRunScoring} loading={triggerScore.isPending}>
                        <Sparkles size={15} aria-hidden="true" />
                        {triggerScore.isPending ? t("upload.scoring") : t("upload.runScoring")}
                      </Button>
                    )
                  ) : null}
                </div>
              ) : null}

              {step === "done" ? (
                <div className="nw-card nw-intake-done-card">
                  <div className="nw-intake-done-icon">
                    <CheckCircle2 size={28} aria-hidden="true" />
                  </div>
                  <p className="nw-intake-done-title">{t("upload.done.title")}</p>
                  <p className="nw-intake-done-body">
                    {t("upload.done.body", { count: uploadResult?.row_count ?? 0 })}
                  </p>
                  {doneStats ? (
                    <div className="nw-intake-done-stats">
                      <div>
                        <div className="nw-intake-done-stat-value">{doneStats.scored}</div>
                        <div className="nw-intake-done-stat-label">{t("upload.done.scored")}</div>
                      </div>
                      <div>
                        <div className="nw-intake-done-stat-value">{doneStats.shortlisted}</div>
                        <div className="nw-intake-done-stat-label">
                          {t("upload.done.shortlisted")}
                        </div>
                      </div>
                      <div>
                        <div className="nw-intake-done-stat-value">{doneStats.avg.toFixed(1)}</div>
                        <div className="nw-intake-done-stat-label">{t("upload.done.avgScore")}</div>
                      </div>
                    </div>
                  ) : null}
                  <div className="nw-intake-done-actions">
                    <Link href={Routes.intake.cycle(cycleId)} className="nw-btn nw-btn-primary">
                      {t("upload.done.viewShortlist")}
                      <ArrowRight size={15} aria-hidden="true" />
                    </Link>
                    {has("nawa:iam:manage") ? (
                      <Link href={Routes.admin.audit} className="nw-btn nw-btn-secondary">
                        {t("upload.done.viewAudit")}
                      </Link>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </>
          )}
        </Guard>
      </div>
    </ConsoleShell>
  );
}
