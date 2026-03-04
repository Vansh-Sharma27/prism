"use client";

import { useCallback, useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { PageHeader, SectionHeader } from "@/components/PageHeader";
import { PollingNotice } from "@/components/PollingNotice";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import {
  fetchActivityEvents,
  fetchAdminAnalytics,
  fetchAdminSensors,
  type ActivityEvent,
  type AdminAnalyticsData,
} from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

const ANALYTICS_WINDOWS = [1, 7, 14, 30];
const OFFLINE_THRESHOLDS = [60, 90, 120, 300];

function parseUtcIsoToEpochMs(value: string | null): number {
  if (!value) {
    return 0;
  }

  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
  const normalized = hasTimezone ? value : `${value}Z`;
  const parsed = Date.parse(normalized);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function formatIsoUtcTime(value: string | null): string {
  const epochMs = parseUtcIsoToEpochMs(value);
  if (!epochMs) {
    return "--:--";
  }
  return new Date(epochMs).toISOString().slice(11, 16);
}

function formatHourLabel(hour: number): string {
  return `${hour.toString().padStart(2, "0")}:00`;
}

function formatTimeMs(value: number): string {
  if (!value) {
    return "--:--:--";
  }
  return new Date(value).toISOString().slice(11, 19);
}

function csvEscape(value: string | number | null | undefined): string {
  const raw = value == null ? "" : String(value);
  if (!raw.includes(",") && !raw.includes('"') && !raw.includes("\n")) {
    return raw;
  }
  return `"${raw.replace(/"/g, '""')}"`;
}

function buildAdminAnalyticsCsv(analytics: AdminAnalyticsData): string {
  const rows: string[] = [];
  rows.push("PRISM Admin Analytics Export");
  rows.push(`Window Days,${analytics.windowDays}`);
  rows.push(`Generated At UTC,${csvEscape(analytics.generatedAt)}`);
  rows.push(`Peak Hour UTC,${csvEscape(analytics.peakHour.hourUtc)}`);
  rows.push(`Peak Hour Events,${analytics.peakHour.events}`);
  rows.push("");

  rows.push("Daily Occupancy Average");
  rows.push("Date,Average Occupancy %,Samples");
  for (const row of analytics.dailyOccupancyAverage) {
    rows.push(
      [
        csvEscape(row.date),
        csvEscape(row.avgOccupancyPct),
        csvEscape(row.samples),
      ].join(",")
    );
  }
  rows.push("");

  rows.push("Hourly Event Distribution");
  rows.push("Hour UTC,Events");
  for (const row of analytics.hourlyEventDistribution) {
    rows.push([csvEscape(formatHourLabel(row.hour)), csvEscape(row.events)].join(","));
  }
  rows.push("");

  rows.push("Zone Utilization Comparison");
  rows.push("Zone ID,Zone Name,Lot ID,Lot Name,Occupied Slots,Total Slots,Utilization %");
  for (const row of analytics.zoneUtilizationComparison) {
    rows.push(
      [
        csvEscape(row.zoneId),
        csvEscape(row.zoneName),
        csvEscape(row.lotId),
        csvEscape(row.lotName),
        csvEscape(row.occupiedSlots),
        csvEscape(row.totalSlots),
        csvEscape(row.utilizationPct),
      ].join(",")
    );
  }

  return rows.join("\n");
}

export function AdminClient() {
  const [windowDays, setWindowDays] = useState(7);
  const [offlineThresholdSeconds, setOfflineThresholdSeconds] = useState(90);

  const fetchSensors = useCallback(
    () => fetchAdminSensors(offlineThresholdSeconds),
    [offlineThresholdSeconds]
  );
  const fetchAnalytics = useCallback(
    () => fetchAdminAnalytics(windowDays),
    [windowDays]
  );
  const fetchRecentEvents = useCallback(() => fetchActivityEvents(40), []);

  const {
    data: sensorData,
    loading: sensorsLoading,
    refreshing: sensorsRefreshing,
    error: sensorsError,
    retry: retrySensors,
  } = usePolling(fetchSensors, 5000);

  const {
    data: analyticsData,
    loading: analyticsLoading,
    refreshing: analyticsRefreshing,
    error: analyticsError,
    retry: retryAnalytics,
  } = usePolling(fetchAnalytics, 12000);

  const {
    data: activityData,
    error: activityError,
    retry: retryActivity,
  } = usePolling<ActivityEvent[]>(fetchRecentEvents, 7000);

  const sensorRows = useMemo(() => sensorData?.sensors ?? [], [sensorData?.sensors]);
  const sensorSummary = sensorData?.summary || {
    totalSensors: 0,
    onlineSensors: 0,
    degradedSensors: 0,
    offlineSensors: 0,
    offlineThresholdSeconds,
  };

  const analytics = analyticsData || {
    windowDays,
    dailyOccupancyAverage: [],
    peakHour: { hourUtc: null, events: 0 },
    hourlyEventDistribution: [],
    zoneUtilizationComparison: [],
    generatedAt: "",
  };

  const recentEvents = activityData || [];
  const entries = recentEvents.filter((event) => event.type === "entry").length;
  const exits = recentEvents.filter((event) => event.type === "exit").length;
  const netFlow = entries - exits;
  const latestEventTime = recentEvents.reduce((maxTs, event) => Math.max(maxTs, event.timestamp), 0);

  const occupancySummary = useMemo(() => {
    const totalSlots = sensorRows.reduce((sum, row) => sum + row.totalSlots, 0);
    const occupiedSlots = sensorRows.reduce((sum, row) => sum + row.occupiedSlots, 0);
    const occupancyRate = totalSlots > 0 ? Math.round((occupiedSlots / totalSlots) * 100) : 0;
    return { totalSlots, occupiedSlots, occupancyRate };
  }, [sensorRows]);

  const hourlyPeak = analytics.hourlyEventDistribution.reduce(
    (maxEvents, row) => Math.max(maxEvents, row.events),
    0
  );

  const topZone = analytics.zoneUtilizationComparison[0] || null;
  const loading = sensorsLoading || analyticsLoading;
  const refreshing = sensorsRefreshing || analyticsRefreshing;
  const combinedError = sensorsError || analyticsError || activityError;
  const canExportCsv =
    !!analyticsData &&
    analyticsData.windowDays === windowDays &&
    !analyticsLoading &&
    !analyticsRefreshing;

  const handleExportCsv = useCallback(() => {
    if (!analyticsData || analyticsData.windowDays !== windowDays) {
      return;
    }

    const csv = buildAdminAnalyticsCsv(analyticsData);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const href = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = href;
    link.download = `prism-admin-analytics-${analyticsData.windowDays}d.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(href);
  }, [analyticsData, windowDays]);

  return (
    <ProtectedRoute requireRole="admin">
      <AppShell>
        <PageHeader
          title="Admin Control"
          subtitle="Sensor fleet health and historical analytics"
        >
          <div className="flex flex-wrap items-center gap-4 border border-[var(--border-default)] bg-[var(--bg-secondary)] px-4 py-2">
            <div className="flex items-center gap-2">
              <span className="label-quiet">Sensors</span>
              <span className="font-mono text-lg font-bold text-[var(--text-primary)]">
                {sensorSummary.totalSensors.toString().padStart(2, "0")}
              </span>
            </div>
            <div className="h-6 w-px bg-[var(--border-default)]" />
            <div className="flex items-center gap-2">
              <span className="label-quiet">Degraded</span>
              <span className="font-mono text-lg font-bold text-[var(--warning)]">
                {sensorSummary.degradedSensors.toString().padStart(2, "0")}
              </span>
            </div>
            <div className="h-6 w-px bg-[var(--border-default)]" />
            <div className="flex items-center gap-2">
              <span className="label-quiet">Offline</span>
              <span className="font-mono text-lg font-bold text-[var(--occupied)]">
                {sensorSummary.offlineSensors.toString().padStart(2, "0")}
              </span>
            </div>
            <div className="h-6 w-px bg-[var(--border-default)]" />
            <div className="flex items-center gap-2">
              <span className="label-quiet">Window</span>
              <span className="font-mono text-sm text-[var(--accent)]">
                {analytics.windowDays}d
              </span>
            </div>
            {refreshing && (
              <>
                <div className="h-6 w-px bg-[var(--border-default)]" />
                <span className="font-mono text-xs text-[var(--accent)]">SYNC...</span>
              </>
            )}
          </div>
        </PageHeader>

        {combinedError && (
          <PollingNotice
            message={combinedError}
            actions={[
              { label: "Retry Sensors", onClick: retrySensors },
              { label: "Retry Analytics", onClick: retryAnalytics },
              { label: "Retry Events", onClick: retryActivity },
            ]}
          />
        )}

        <section className="mb-6 border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4" aria-label="Admin filters and export">
          <div className="grid gap-4 md:grid-cols-3">
            <label className="space-y-1">
              <span className="label-quiet">Analytics Window</span>
              <select
                value={windowDays}
                onChange={(event) => setWindowDays(Number(event.target.value))}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
              >
                {ANALYTICS_WINDOWS.map((days) => (
                  <option key={days} value={days}>
                    Last {days} day{days > 1 ? "s" : ""}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1">
              <span className="label-quiet">Sensor Offline Threshold</span>
              <select
                value={offlineThresholdSeconds}
                onChange={(event) => setOfflineThresholdSeconds(Number(event.target.value))}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
              >
                {OFFLINE_THRESHOLDS.map((seconds) => (
                  <option key={seconds} value={seconds}>
                    {seconds}s
                  </option>
                ))}
              </select>
            </label>

            <div className="space-y-1">
              <span className="label-quiet">Export</span>
              <button
                type="button"
                onClick={handleExportCsv}
                disabled={!canExportCsv}
                className="w-full border border-[var(--accent)] bg-[var(--accent)] px-3 py-2 text-xs font-display font-semibold uppercase tracking-wider text-[var(--bg-primary)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {canExportCsv ? "Export CSV" : "Updating..."}
              </button>
            </div>
          </div>
        </section>

        <section className="mb-8" aria-label="Sensor health table">
          <SectionHeader title="Sensor Health" count={sensorRows.length} subtitle={`Offline>${sensorSummary.offlineThresholdSeconds}s`} />
          {loading && sensorRows.length === 0 ? (
            <div className="space-y-2">
              {[1, 2, 3].map((item) => (
                <div key={item} className="skeleton h-12 border border-[var(--border-subtle)]" />
              ))}
            </div>
          ) : sensorRows.length > 0 ? (
            <div className="space-y-3">
              <div className="hidden overflow-hidden border border-[var(--border-default)] bg-[var(--bg-secondary)] md:block">
                <div className="grid grid-cols-6 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-3 font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  <span>Sensor</span>
                  <span className="text-center">Slots</span>
                  <span className="text-center">Occupied</span>
                  <span className="text-center">Last Seen</span>
                  <span className="text-center">Uptime 24h</span>
                  <span className="text-center">Status</span>
                </div>
                {sensorRows.map((row) => (
                  <div key={row.sensorId} className="grid grid-cols-6 border-b border-[var(--border-subtle)] px-4 py-3 font-mono text-sm last:border-b-0">
                    <span className="font-semibold text-[var(--text-primary)]">{row.sensorId}</span>
                    <span className="text-center text-[var(--text-secondary)]">{row.totalSlots}</span>
                    <span className="text-center text-[var(--warning)]">{row.occupiedSlots}</span>
                    <span className="text-center text-[var(--accent)]">{formatIsoUtcTime(row.lastSeenAt)} UTC</span>
                    <span className="text-center text-[var(--vacant)]">{row.uptime24hPct.toFixed(1)}%</span>
                    <span
                      className={`text-center uppercase ${
                        row.status === "online"
                          ? "text-[var(--vacant)]"
                          : row.status === "degraded"
                            ? "text-[var(--warning)]"
                            : "text-[var(--occupied)]"
                      }`}
                    >
                      {row.status}
                    </span>
                  </div>
                ))}
              </div>

              <div className="space-y-2 md:hidden">
                {sensorRows.map((row) => (
                  <article key={row.sensorId} className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-3">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                        {row.sensorId}
                      </h3>
                      <span
                        className={`font-display text-[10px] font-semibold uppercase tracking-wider ${
                          row.status === "online"
                            ? "text-[var(--vacant)]"
                            : row.status === "degraded"
                              ? "text-[var(--warning)]"
                              : "text-[var(--occupied)]"
                        }`}
                      >
                        {row.status}
                      </span>
                    </div>
                    <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                      <div className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                        <dt className="label-quiet">Slots</dt>
                        <dd className="font-mono text-[var(--text-secondary)]">{row.totalSlots}</dd>
                      </div>
                      <div className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                        <dt className="label-quiet">Occupied</dt>
                        <dd className="font-mono text-[var(--warning)]">{row.occupiedSlots}</dd>
                      </div>
                      <div className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                        <dt className="label-quiet">Last Seen (UTC)</dt>
                        <dd className="font-mono text-[var(--accent)]">{formatIsoUtcTime(row.lastSeenAt)}</dd>
                      </div>
                      <div className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                        <dt className="label-quiet">Uptime 24h</dt>
                        <dd className="font-mono text-[var(--vacant)]">{row.uptime24hPct.toFixed(1)}%</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            </div>
          ) : (
            <div className="border border-[var(--border-default)] bg-[var(--bg-secondary)] px-4 py-6 text-sm text-[var(--text-muted)]">
              No sensor telemetry yet. Start simulator or firmware nodes.
            </div>
          )}
        </section>

        <section className="grid gap-4 lg:grid-cols-2" aria-label="Analytics overview">
          <article className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4">
            <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
              Hourly Event Distribution
            </h2>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Event load by UTC hour from server-side analytics ({analytics.windowDays}d window).
            </p>

            {analytics.hourlyEventDistribution.length > 0 ? (
              <div className="mt-4 overflow-x-auto border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-3">
                <div className="flex min-w-[36rem] items-end gap-2">
                  {analytics.hourlyEventDistribution.map((bucket) => {
                    const percent = hourlyPeak > 0 ? (bucket.events / hourlyPeak) * 100 : 0;
                    const barHeight = Math.max(percent, bucket.events > 0 ? 8 : 2);
                    return (
                      <div key={bucket.hour} className="flex w-6 flex-col items-center gap-1">
                        <div className="flex h-24 w-full items-end rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-primary)] px-1 py-1">
                          <div
                            className="w-full rounded-[1px] bg-[var(--accent)]/75"
                            style={{ height: `${barHeight}%` }}
                            aria-label={`${formatHourLabel(bucket.hour)}: ${bucket.events} events`}
                          />
                        </div>
                        <span className="font-mono text-[10px] text-[var(--text-muted)]">
                          {bucket.hour.toString().padStart(2, "0")}
                        </span>
                        <span className="font-mono text-[10px] text-[var(--text-secondary)]">
                          {bucket.events}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="mt-4 border border-dashed border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-6 text-xs text-[var(--text-muted)]">
                No analytics samples available in the selected window.
              </div>
            )}
          </article>

          <article className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4">
            <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
              Operational Signals
            </h2>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Combined telemetry and event indicators for admin operations.
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                <dt className="label-quiet">Occupancy</dt>
                <dd className="font-mono text-[var(--accent)]">{occupancySummary.occupancyRate}%</dd>
              </div>
              <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                <dt className="label-quiet">Net Flow</dt>
                <dd className={`font-mono ${netFlow >= 0 ? "text-[var(--warning)]" : "text-[var(--vacant)]"}`}>
                  {netFlow >= 0 ? "+" : ""}
                  {netFlow}
                </dd>
              </div>
              <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                <dt className="label-quiet">Peak Hour (UTC)</dt>
                <dd className="font-mono text-[var(--text-primary)]">
                  {analytics.peakHour.hourUtc || "--:--"} ({analytics.peakHour.events})
                </dd>
              </div>
              <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                <dt className="label-quiet">Top Zone</dt>
                <dd className="font-mono text-[var(--text-primary)]">
                  {topZone ? `${topZone.zoneName} (${topZone.utilizationPct}%)` : "--"}
                </dd>
              </div>
              <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                <dt className="label-quiet">Last Event (UTC)</dt>
                <dd className="font-mono text-[var(--accent)]">{formatTimeMs(latestEventTime)}</dd>
              </div>
              <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                <dt className="label-quiet">Generated At (UTC)</dt>
                <dd className="font-mono text-[var(--accent)]">{formatIsoUtcTime(analytics.generatedAt)}</dd>
              </div>
            </dl>

            <div className="mt-4 max-h-40 space-y-2 overflow-y-auto">
              {recentEvents.slice(0, 8).map((event) => (
                <div key={event.id} className="flex items-center justify-between border border-[var(--border-subtle)] px-3 py-2 text-xs">
                  <span className="font-mono text-[var(--text-primary)]">{event.slot}</span>
                  <span className="font-display uppercase text-[var(--text-muted)]">{event.type}</span>
                  <span className="font-mono text-[var(--accent)]">{formatTimeMs(event.timestamp)}</span>
                </div>
              ))}
              {recentEvents.length === 0 && (
                <div className="border border-dashed border-[var(--border-subtle)] px-3 py-3 text-xs text-[var(--text-muted)]">
                  No recent events available.
                </div>
              )}
            </div>
          </article>
        </section>
      </AppShell>
    </ProtectedRoute>
  );
}
