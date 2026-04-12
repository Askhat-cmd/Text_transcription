import { useCallback, useEffect, useState } from 'react';
import type { InlineTrace } from '../types';
import { storageService } from '../services/storage.service';

export interface SessionMetrics {
  total_turns: number;
  fast_path_pct: number;
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
      const apiKey = storageService.getApiKey();
      const headers = apiKey ? { 'X-API-Key': apiKey } : undefined;
      const [metricsRes, tracesRes] = await Promise.all([
        fetch(`/api/debug/session/${sessionId}/metrics`, { credentials: 'include', headers }),
        fetch(`/api/debug/session/${sessionId}/traces`, { credentials: 'include', headers }),
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
