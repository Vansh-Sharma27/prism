"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface PollingState<T> {
  data: T | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refreshedAt: number | null;
  retry: () => void;
}

export function usePolling<T>(fetchFn: () => Promise<T>, intervalMs = 10000): PollingState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<number | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const hasFetchedAtLeastOnce = useRef(false);

  const retry = useCallback(() => {
    setRetryNonce((value) => value + 1);
  }, []);

  useEffect(() => {
    let mounted = true;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      const initialLoad = !hasFetchedAtLeastOnce.current;
      if (initialLoad) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      try {
        const result = await fetchFn();
        if (!mounted) {
          return;
        }

        setData(result);
        setError(null);
        setRefreshedAt(Math.floor(Date.now() / 1000));
      } catch (err) {
        if (!mounted) {
          return;
        }

        const message = err instanceof Error ? err.message : "Unexpected polling error";
        setError(message);
      } finally {
        if (mounted) {
          hasFetchedAtLeastOnce.current = true;
          setLoading(false);
          setRefreshing(false);
          timeoutId = setTimeout(poll, intervalMs);
        }
      }
    };

    poll();

    return () => {
      mounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [fetchFn, intervalMs, retryNonce]);

  return { data, loading, refreshing, error, refreshedAt, retry };
}
