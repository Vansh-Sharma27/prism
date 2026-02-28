/**
 * Format a unix timestamp to HH:MM:SS
 */
export function formatTimestamp(ts: number): string {
  const date = new Date(ts * 1000);
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Format a JS timestamp to HH:MM:SS (for Date.now()-style values)
 */
export function formatTime(ts: number): string {
  const date = new Date(ts);
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Format a JS timestamp to MM/DD/YYYY
 */
export function formatDate(ts: number): string {
  const date = new Date(ts);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

/**
 * Format relative time (e.g., "5s ago", "3m ago")
 */
export function formatRelativeTime(ts: number): string {
  const diff = Math.floor((Date.now() - ts) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}
