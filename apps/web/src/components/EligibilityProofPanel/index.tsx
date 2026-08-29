"use client";

import Button from "@/components/Button";
import Callout from "@/components/Callout";
import Input from "@/components/Input";
import Select from "@/components/Select";
import { type EligibilityVerdict, useRecordEligibilityProof } from "@/hooks/Intake";
import { useT } from "@/i18n/useT";
import { useState } from "react";
import "./styles.css";

export interface IProps {
  applicationId: string;
  // Called after a proof is recorded so the parent can refresh the audit/history.
  onRecorded?: () => void;
}

const NETWORKS = ["undeployed", "preview", "preprod"];

// Records a Midnight ZK eligibility proof reference against the application
// (gated `nawa:intake:ingest`). The proof is generated client-side by the
// midnight-eligibility contract; a reviewer pastes the reference it prints —
// the deployed contract address and the proof tx id — plus the verdict. The
// applicant's age and funding never reach NAWA; only this reference is stored,
// in the immutable audit log.
export default function EligibilityProofPanel({ applicationId, onRecorded }: IProps) {
  const t = useT("intake");
  const record = useRecordEligibilityProof(applicationId);
  const [contractAddress, setContractAddress] = useState("");
  const [txId, setTxId] = useState("");
  const [verdict, setVerdict] = useState<EligibilityVerdict>("eligible");
  const [network, setNetwork] = useState("undeployed");
  const [minAge, setMinAge] = useState("");
  const [maxFunding, setMaxFunding] = useState("");
  const [touched, setTouched] = useState(false);
  const [recordedRef, setRecordedRef] = useState<string | null>(null);

  const contractMissing = contractAddress.trim().length === 0;
  const txMissing = txId.trim().length === 0;
  const missing = contractMissing || txMissing;

  async function handleSubmit() {
    setTouched(true);
    if (missing) return;
    setRecordedRef(null);
    try {
      const result = await record.run({
        contractAddress: contractAddress.trim(),
        txId: txId.trim(),
        verdict,
        network,
        minAge: minAge.trim() ? Number(minAge) : null,
        maxPriorFunding: maxFunding.trim() ? Number(maxFunding) : null,
      });
      setRecordedRef(result.proof_ref);
      setContractAddress("");
      setTxId("");
      setMinAge("");
      setMaxFunding("");
      setTouched(false);
      onRecorded?.();
    } catch {
      // Surfaced via record.error below.
    }
  }

  return (
    <div className="nw-eligibility-panel">
      <p className="nw-intake-subtitle">{t("eligibility.description")}</p>
      <Input
        label={t("eligibility.contractAddress")}
        value={contractAddress}
        onChange={(event) => setContractAddress(event.target.value)}
        error={touched && contractMissing ? t("eligibility.required") : undefined}
      />
      <Input
        label={t("eligibility.txId")}
        value={txId}
        onChange={(event) => setTxId(event.target.value)}
        error={touched && txMissing ? t("eligibility.required") : undefined}
      />
      <Select
        label={t("eligibility.verdict")}
        value={verdict}
        onChange={(event) => setVerdict(event.target.value as EligibilityVerdict)}
        options={[
          { value: "eligible", label: t("eligibility.verdictEligible") },
          { value: "ineligible", label: t("eligibility.verdictIneligible") },
        ]}
      />
      <Select
        label={t("eligibility.networkLabel")}
        value={network}
        onChange={(event) => setNetwork(event.target.value)}
        options={NETWORKS.map((n) => ({ value: n, label: n }))}
      />
      <Input
        label={t("eligibility.minAge")}
        value={minAge}
        inputMode="numeric"
        onChange={(event) => setMinAge(event.target.value)}
      />
      <Input
        label={t("eligibility.maxFunding")}
        value={maxFunding}
        inputMode="numeric"
        onChange={(event) => setMaxFunding(event.target.value)}
      />
      {recordedRef ? (
        <Callout tone="success">{t("eligibility.recorded", { ref: recordedRef })}</Callout>
      ) : null}
      {record.error ? (
        <p className="nw-input-error-text" role="alert">
          {t("eligibility.error")}
        </p>
      ) : null}
      <Button onClick={handleSubmit} loading={record.isPending} disabled={missing}>
        {record.isPending ? t("eligibility.submitting") : t("eligibility.submit")}
      </Button>
    </div>
  );
}
