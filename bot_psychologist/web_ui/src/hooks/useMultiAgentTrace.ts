import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { apiService } from '../services/api.service';
import type { MultiAgentTraceData } from '../types';

interface UseMultiAgentTraceResult {
  trace: MultiAgentTraceData | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

function extractTurnIndex(messageId: string): number | undefined {
  const match = messageId.match(/-b-(\d+)$/);
  if (!match) {
    return undefined;
  }
  const value = Number(match[1]);
  if (!Number.isFinite(value)) {
    return undefined;
  }
  // В useChat bot-id формируется как 0-based индекс (`...-b-0`, `...-b-1`),
  // а backend хранит multiagent turn_index как 1-based.
  return value + 1;
}

export function useMultiAgentTrace(
  sessionId: string | undefined,
  messageId: string,
  enabled: boolean
): UseMultiAgentTraceResult {
  const [trace, setTrace] = useState<MultiAgentTraceData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestSeqRef = useRef(0);

  const turnIndex = useMemo(() => extractTurnIndex(messageId), [messageId]);

  const fetchTrace = useCallback(async () => {
    if (!sessionId || !enabled) {
      setTrace(null);
      setError(null);
      return;
    }
    const requestSeq = requestSeqRef.current + 1;
    requestSeqRef.current = requestSeq;
    setIsLoading(true);
    setError(null);
    try {
      const maxAttempts = turnIndex !== undefined ? 3 : 1;
      const retryDelayMs = 250;

      for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
        try {
          const data = await apiService.getMultiAgentTrace(sessionId, turnIndex);
          if (requestSeq !== requestSeqRef.current) {
            return;
          }
          setTrace(data);
          setError(null);
          return;
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Trace unavailable';
          const isNotFound = /not found/i.test(message);
          const canRetry = isNotFound && attempt < maxAttempts;

          if (canRetry) {
            await new Promise((resolve) => {
              window.setTimeout(resolve, retryDelayMs);
            });
            continue;
          }
          if (requestSeq !== requestSeqRef.current) {
            return;
          }
          setError(message);
          setTrace((prev) => (isNotFound && prev ? prev : null));
          return;
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Trace unavailable';
      if (requestSeq !== requestSeqRef.current) {
        return;
      }
      setError(message);
      setTrace(null);
    } finally {
      if (requestSeq === requestSeqRef.current) {
        setIsLoading(false);
      }
    }
  }, [enabled, sessionId, turnIndex]);

  useEffect(() => {
    void fetchTrace();
  }, [fetchTrace]);

  return {
    trace,
    isLoading,
    error,
    refetch: () => {
      void fetchTrace();
    },
  };
}
