"use client";

import { Button, Callout, Card, Input, Progress } from "@/components";
import { usePermissions } from "@/hooks/Auth";
import {
  useCycles,
  useScoreProgress,
  useTriggerScore,
  useUpload,
  useUploadProgress,
} from "@/hooks/Intake";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { Routes } from "@nawa/contracts";
import Link from "next/link";
import { type ChangeEvent, type DragEvent, useMemo, useState } from "react";
import "./styles.css";

type Target = "applicant_name" | "applicant_email" | "phone" | "country" | "question" | "skip";

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

// Screening console upload view (design-system §6.3.1, `/intake`). Cycle
// picker, drag-drop upload with a column-mapping preview, and the live
// progress panel driven by the upload/score SSE relays. Single-application
// entry isn't wired here — its backend route stays deferred (only bulk
// upload, scoring, and dedup-resolution routes were built this chunk).
export default function IntakeWrapper() {
  const t = useT("intake");
  const { cycles, isLoading: cyclesLoading } = useCycles();
  const { has } = usePermissions();

  const [cycleId, setCycleId] = useState("");
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

  const columnMap = useMemo(() => buildColumnMap(rows), [rows]);

  function handleFile(next: File | null) {
    setFile(next);
    setUploadResult(null);
    setScoringStarted(false);
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

  return (
    <ConsoleShell title={t("upload.title")}>
      <Guard permission="nawa:console:intake">
        <p className="nw-intake-subtitle">{t("upload.subtitle")}</p>

        <Card className="nw-intake-picker">
          <label className="nw-label" htmlFor="intake-cycle-picker">
            {t("upload.cyclePicker.label")}
          </label>
          <select
            id="intake-cycle-picker"
            className="nw-select"
            value={cycleId}
            onChange={(event) => {
              setCycleId(event.target.value);
              setUploadResult(null);
              setScoringStarted(false);
            }}
            disabled={cyclesLoading}
          >
            <option value="">{t("upload.cyclePicker.placeholder")}</option>
            {(cycles ?? []).map((cycle) => (
              <option key={cycle.id} value={cycle.id}>
                {cycle.program_name_en ?? cycle.program_name_ar} — {cycle.name_en ?? cycle.name_ar}
              </option>
            ))}
          </select>
        </Card>

        <Card
          className="nw-intake-dropzone"
          onDragOver={(event) => event.preventDefault()}
          onDrop={onDrop}
        >
          <p>{t("upload.dropzone.label")}</p>
          <p className="nw-intake-dropzone-hint">{t("upload.dropzone.hint")}</p>
          <label className="nw-btn nw-btn-secondary">
            {t("upload.dropzone.chooseFile")}
            <input
              type="file"
              accept=".csv,.xlsx,.json"
              onChange={onFileInput}
              className="nw-intake-file-input"
            />
          </label>
          {file ? <p className="nw-intake-filename">{file.name}</p> : null}
        </Card>

        {rows.length > 0 || file ? (
          <Card className="nw-intake-column-map">
            <h3>{t("upload.columnMap.title")}</h3>
            <p className="nw-intake-subtitle">{t("upload.columnMap.subtitle")}</p>
            {rows.map((row, index) => (
              <div className="nw-intake-map-row" key={`${row.source}-${index}`}>
                <Input
                  aria-label={t("upload.columnMap.title")}
                  value={row.source}
                  onChange={(event) => updateRow(index, { source: event.target.value })}
                  placeholder="column"
                />
                <select
                  className="nw-select"
                  value={row.target}
                  onChange={(event) => updateRow(index, { target: event.target.value as Target })}
                >
                  {TARGETS.map((target) => (
                    <option key={target} value={target}>
                      {t(`upload.columnMap.${TARGET_I18N_KEY[target]}`)}
                    </option>
                  ))}
                </select>
                {row.target === "question" ? (
                  <Input
                    aria-label={t("upload.columnMap.questionKey")}
                    value={row.questionKey}
                    onChange={(event) => updateRow(index, { questionKey: event.target.value })}
                    placeholder={t("upload.columnMap.questionKey")}
                  />
                ) : null}
              </div>
            ))}
            <Button variant="ghost" onClick={addRow}>
              +
            </Button>
          </Card>
        ) : null}

        {error ? <Callout tone="info">{error}</Callout> : null}

        <Button onClick={handleUpload} loading={upload.isPending} disabled={!cycleId || !file}>
          {upload.isPending ? t("upload.submitting") : t("upload.submit")}
        </Button>

        {uploadResult ? (
          <Card className="nw-intake-progress">
            <p>{t("upload.uploadedSummary", { count: uploadResult.row_count })}</p>
            <Progress
              value={uploadProgress.done + uploadProgress.failed}
              max={uploadProgress.total || 1}
              label={t("upload.progress.normalizing", {
                done: uploadProgress.done,
                total: uploadProgress.total,
              })}
              valueText={`${uploadProgress.done}/${uploadProgress.total}`}
            />
            {uploadProgress.stoppedReason ? (
              <Callout tone="info">
                {t("upload.progress.stopped", { reason: uploadProgress.stoppedReason })}
              </Callout>
            ) : null}

            {has("nawa:intake:score") ? (
              <Button onClick={handleRunScoring} loading={triggerScore.isPending}>
                {triggerScore.isPending ? t("upload.scoring") : t("upload.runScoring")}
              </Button>
            ) : null}

            {scoringStarted ? (
              <Progress
                value={scoreProgress.done + scoreProgress.failed}
                max={scoreProgress.total || 1}
                label={t("upload.progress.scoring", {
                  done: scoreProgress.done,
                  total: scoreProgress.total,
                })}
                valueText={`${scoreProgress.done}/${scoreProgress.total}`}
              />
            ) : null}

            <Link href={Routes.intake.cycle(cycleId)} className="nw-btn nw-btn-secondary">
              {t("shortlist.title")}
            </Link>
          </Card>
        ) : null}
      </Guard>
    </ConsoleShell>
  );
}
