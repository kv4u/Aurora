import { useState, useEffect, useCallback } from "react";

/**
 * Generic data-fetching hook with loading/error states and auto-refresh.
 *
 * @param {Function} fetcher  — async function returning data
 * @param {object} opts       — { deps: [], refreshInterval: ms, enabled: true }
 */
export default function useApi(fetcher, opts = {}) {
  const { deps = [], refreshInterval = 0, enabled = true } = opts;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!enabled) return;
    try {
      setError(null);
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useEffect(() => {
    if (!refreshInterval || !enabled) return;
    const id = setInterval(load, refreshInterval);
    return () => clearInterval(id);
  }, [load, refreshInterval, enabled]);

  return { data, loading, error, refresh: load };
}
