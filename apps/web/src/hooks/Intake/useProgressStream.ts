"use client";

import { useEffect, useRef, useState } from "react";

export interface ProgressSnapshot {
  total: number;
  done: number;
  failed: number;
  stoppedReason: string | null;
}

interface ProgressEvent {
  type: "snapshot" | "progress" | "stopped";
  total?: number;
  done?: number;
  failed?: number;
  stopped_reason?: string | null;
  status?: string;
  reason?: string;
}

const INITIAL: ProgressSnapshot = { total: 0, done: 0, failed: 0, stoppedReason: null };

// Subscribes to one of the intake domain's per-run SSE relays
// (events:intake:upload:<id> / events:intake:score:<cycle_id>,
// 06-intake-copilot.md §6.3.1). The server sends one snapshot frame of the
// current Redis progress hash on connect, then a `progress` event per item
// and an optional `stopped` event. This mirrors the SAME done/failed
// accounting the backend hash uses locally rather than re-polling —
// `okStatus` is the per-item status that counts as "done" (upload uses
// "normalized" vs "normalize_failed"; scoring uses "scored" vs anything
// else), matching jobs/normalize_applications.py's and jobs/score_cycle.py's
// own field-increment rule exactly.
export function useProgressStream(path: string | null, okStatus: string): ProgressSnapshot {
  const [snapshot, setSnapshot] = useState<ProgressSnapshot>(INITIAL);
  const okStatusRef = useRef(okStatus);
  okStatusRef.current = okStatus;

  useEffect(() => {
    if (!path) {
      setSnapshot(INITIAL);
      return;
    }
    setSnapshot(INITIAL);
    const source = new EventSource(`/api${path}`);
    source.onmessage = (event) => {
      const payload = JSON.parse(event.data) as ProgressEvent;
      if (payload.type === "snapshot") {
        setSnapshot({
          total: payload.total ?? 0,
          done: payload.done ?? 0,
          failed: payload.failed ?? 0,
          stoppedReason: payload.stopped_reason ?? null,
        });
      } else if (payload.type === "progress") {
        const ok = payload.status === okStatusRef.current;
        setSnapshot((prev) => ({
          ...prev,
          done: prev.done + (ok ? 1 : 0),
          failed: prev.failed + (ok ? 0 : 1),
        }));
      } else if (payload.type === "stopped") {
        setSnapshot((prev) => ({ ...prev, stoppedReason: payload.reason ?? "stopped" }));
      }
    };
    return () => source.close();
  }, [path]);

  return snapshot;
}

export function useUploadProgress(uploadId: string | null): ProgressSnapshot {
  return useProgressStream(uploadId ? `/intake/uploads/${uploadId}/events` : null, "normalized");
}

export function useScoreProgress(cycleId: string | null): ProgressSnapshot {
  return useProgressStream(cycleId ? `/intake/cycles/${cycleId}/score/events` : null, "scored");
}
