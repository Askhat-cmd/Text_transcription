import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { apiService, TraceUnavailableError } from '../services/api.service';
import type { MultiAgentTraceData, TraceAvailability } from '../types';

interface UseMultiAgentTraceResult {
  trace: MultiAgentTraceData | null;
  availability: TraceAvailability | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

function extractLegacyTurnIndex(messageId: string): number | undefined {
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
  turnNumber: number | undefined,
  enabled: boolean
): UseMultiAgentTraceResult {
  const [trace, setTrace] = useState<MultiAgentTraceData | null>(null);
  const [availability, setAvailability] = useState<TraceAvailability | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestSeqRef = useRef(0);

  const turnIndex = useMemo(
    () => turnNumber ?? extractLegacyTurnIndex(messageId),
    [messageId, turnNumber]
  );

  const fetchTrace = useCallback(async () => {
    if (!sessionId || !enabled) {
      setTrace(null);
      setAvailability(null);
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
          if (
            turnIndex !== undefined &&
            data.turn_index !== undefined &&
            data.turn_index !== null &&
            data.turn_index !== turnIndex
          ) {
            setAvailability({
              status: 'unavailable',
              requested_turn_index: turnIndex,
              resolved_turn_index: data.turn_index,
              exact_turn_match: false,
              reason_code: 'turn_mismatch',
              reason: `Expected trace for turn ${turnIndex}, got turn ${data.turn_index}`,
              resolved_session_id: data.session_id,
              available_turn_indices: data.trace_availability?.available_turn_indices ?? [],
            });
            setError(`Trace turn mismatch: expected ${turnIndex}, got ${data.turn_index}`);
            setTrace(null);
            return;
          }
          setTrace(data);
          setAvailability(data.trace_availability ?? null);
          setError(null);
          return;
        } catch (err) {
          if (err instanceof TraceUnavailableError) {
            const canRetry =
              err.availability?.status === 'unavailable' &&
              attempt < maxAttempts;

            if (canRetry) {
              await new Promise((resolve) => {
                window.setTimeout(resolve, retryDelayMs);
              });
              continue;
            }
            if (requestSeq !== requestSeqRef.current) {
              return;
            }
            setAvailability(err.availability);
            setError(err.message);
            setTrace(null);
            return;
          }
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
          setAvailability(null);
          setError(message);
          setTrace(null);
          return;
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Trace unavailable';
      if (requestSeq !== requestSeqRef.current) {
        return;
      }
      setAvailability(null);
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
    availability,
    isLoading,
    error,
    refetch: () => {
      void fetchTrace();
    },
  };
}
