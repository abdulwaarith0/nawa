"use client";

import { getApiClient } from "@/lib/apiClient";
import { useCallback, useState } from "react";

export interface AssistantCitation {
  source: string;
  page: string | null;
}

export interface AssistantMessage {
  id: string;
  role: "user" | "ai";
  text: string;
  citations?: AssistantCitation[];
}

interface AssistantReply {
  answer: string;
  citations: AssistantCitation[];
}

// Journey assistant (RAG) chat state + send. Backend contract (to be built):
//   POST /journey/cohorts/{cohortId}/assistant  { question }
//        -> { answer: string, citations: [{ source, page }] }
// The answer is AI-generated and rendered under the amber attribution marker.
// No canned/simulated replies here — until the endpoint exists, sending
// surfaces an error bubble rather than a fabricated answer.
export function useJourneyAssistant(cohortId: string | null) {
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [isSending, setIsSending] = useState(false);

  const send = useCallback(
    async (raw: string) => {
      const question = raw.trim();
      if (!question || !cohortId || isSending) return;

      const userMsg: AssistantMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        text: question,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsSending(true);

      try {
        const reply = await getApiClient().post<AssistantReply>(
          `/journey/cohorts/${cohortId}/assistant`,
          { question },
        );
        setMessages((prev) => [
          ...prev,
          {
            id: `a-${Date.now()}`,
            role: "ai",
            text: reply.answer,
            citations: reply.citations,
          },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: `e-${Date.now()}`,
            role: "ai",
            text: "__error__",
          },
        ]);
      } finally {
        setIsSending(false);
      }
    },
    [cohortId, isSending],
  );

  const reset = useCallback(() => setMessages([]), []);

  return { messages, isSending, send, reset };
}
