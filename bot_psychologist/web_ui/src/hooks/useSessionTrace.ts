import { useCallback, useEffect, useState } from 'react';
import type { InlineTrace } from '../types';

export interface SessionMetrics {
  total_turns: number;
  fast_path_pct: number;
  sd_distribution: {
    GREEN: number;
    YELLOW: number;
    RED: number;
  };
  avg_llm_time_ms: number;
  max_llm_time_ms: number;
  total_cost_usd: number;
  turns_with_anomalies: number;
  anomaly_turns_indices: number[];
}

export function useSessionTrace(sessionId?: string | null) {
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const [traces, setTraces] = useState<InlineTrace[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!sessionId) {
      setMetrics(null);
      setTraces([]);
      return;
    }
    setLoading(true);
    try {
      const [metricsRes, tracesRes] = await Promise.all([
        fetch(`/api/debug/session/${sessionId}/metrics`, { credentials: 'include' }),
        fetch(`/api/debug/session/${sessionId}/traces`, { credentials: 'include' }),
      ]);

      if (metricsRes.ok) {
        const metricsData = await metricsRes.json();
        setMetrics(metricsData as SessionMetrics);
      }
      if (tracesRes.ok) {
        const tracesData = await tracesRes.json();
        const list = Array.isArray(tracesData?.traces) ? tracesData.traces : [];
        setTraces(list as InlineTrace[]);
      }
    } catch {
      setMetrics(null);
      setTraces([]);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { metrics, traces, loading, refresh };
}
