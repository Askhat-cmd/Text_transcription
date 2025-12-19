/**
 * useAPI Hook - Generic async data fetching
 * 
 * Handles loading state, error handling, and data caching.
 */

import { useState, useCallback, useRef } from 'react';

export interface UseAPIReturn<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  execute: (...args: unknown[]) => Promise<T>;
  reset: () => void;
}

export function useAPI<T>(
  asyncFunction: (...args: unknown[]) => Promise<T>
): UseAPIReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  // Track if component is mounted
  const isMounted = useRef(true);

  const execute = useCallback(
    async (...args: unknown[]): Promise<T> => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await asyncFunction(...args);
        if (isMounted.current) {
          setData(result);
        }
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Unknown error');
        if (isMounted.current) {
          setError(error);
        }
        throw error;
      } finally {
        if (isMounted.current) {
          setIsLoading(false);
        }
      }
    },
    [asyncFunction]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { data, isLoading, error, execute, reset };
}

/**
 * useAPIOnce - Execute API call on mount
 */
export function useAPIOnce<T>(
  asyncFunction: () => Promise<T>
): UseAPIReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const hasRun = useRef(false);

  const execute = useCallback(async (): Promise<T> => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await asyncFunction();
      setData(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [asyncFunction]);

  // Execute on mount
  if (!hasRun.current) {
    hasRun.current = true;
    execute().catch(() => {
      // Error already handled in state
    });
  }

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
    hasRun.current = false;
  }, []);

  return { data, isLoading, error, execute, reset };
}
