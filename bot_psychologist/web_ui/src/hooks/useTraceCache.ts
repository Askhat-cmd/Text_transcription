import { useCallback, useRef } from 'react';
import type { InlineTrace } from '../types';

const STORAGE_KEY_PREFIX = 'debug_trace_cache_';
const MAX_ENTRIES = 100;

interface TraceEntry {
  messageId: string;
  trace: InlineTrace;
}

export function useTraceCache(chatId: string) {
  const memCache = useRef<Map<string, InlineTrace>>(new Map());
  const lastStorageKey = useRef<string>('');
  const storageKey = `${STORAGE_KEY_PREFIX}${chatId}`;

  const ensureLoaded = useCallback(() => {
    if (lastStorageKey.current !== storageKey) {
      memCache.current.clear();
      lastStorageKey.current = storageKey;
    }
    if (memCache.current.size > 0) return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const entries: TraceEntry[] = JSON.parse(raw);
      entries.forEach(({ messageId, trace }) => {
        memCache.current.set(messageId, trace);
      });
    } catch {
      // Ignore parse errors
    }
  }, [storageKey]);

  const setTrace = useCallback((messageId: string, trace: InlineTrace) => {
    ensureLoaded();
    memCache.current.set(messageId, trace);
    try {
      const entries: TraceEntry[] = Array.from(memCache.current.entries())
        .slice(-MAX_ENTRIES)
        .map(([id, item]) => ({ messageId: id, trace: item }));
      localStorage.setItem(storageKey, JSON.stringify(entries));
    } catch {
      // localStorage may be full
    }
  }, [ensureLoaded, storageKey]);

  const getTrace = useCallback((messageId: string): InlineTrace | undefined => {
    ensureLoaded();
    return memCache.current.get(messageId);
  }, [ensureLoaded]);

  return { setTrace, getTrace };
}
