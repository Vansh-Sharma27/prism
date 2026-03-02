"use client";

import { useEffect, useState } from "react";

interface PollingState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refreshedAt: number | null;
}

export function usePolling<T>(fetchFn: () => Promise<T>, intervalMs = 10000): PollingState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<number | null>(null);

  useEffect(() => {
    let mounted = true;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
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
          setLoading(false);
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
  }, [fetchFn, intervalMs]);

  return { data, loading, error, refreshedAt };
}
