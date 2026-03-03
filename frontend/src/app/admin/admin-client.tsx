"use client";

import { useCallback, useMemo } from "react";
import { AppShell } from "@/components/AppShell";
import { PageHeader, SectionHeader } from "@/components/PageHeader";
import { PollingNotice } from "@/components/PollingNotice";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { fetchActivityEvents, fetchDashboardData, type ActivityEvent } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

type HealthStatus = "online" | "degraded" | "offline";

interface SensorHealthRow {
  sensorId: string;
  totalSlots: number;
  occupiedSlots: number;
  offlineSlots: number;
  lastReading: number;
  status: HealthStatus;
}

interface ActivityBucket {
  label: string;
  entries: number;
  exits: number;
  total: number;
}

function formatUtcTime(ts: number): string {
  if (!ts) {
    return "--:--";
  }
  return new Date(ts * 1000).toISOString().slice(11, 16);
}

function formatUtcTimeMs(ts: number): string {
  if (!ts) {
    return "--:--";
  }
  return new Date(ts).toISOString().slice(11, 16);
}

function deriveHealthStatus(totalSlots: number, offlineSlots: number): HealthStatus {
  if (offlineSlots >= totalSlots) {
    return "offline";
  }
  if (offlineSlots > 0) {
    return "degraded";
  }
  return "online";
}

function buildSensorRows(slotData: Awaited<ReturnType<typeof fetchDashboardData>>["slots"]): SensorHealthRow[] {
  const sensorMap = new Map<string, SensorHealthRow>();

  for (const slot of slotData) {
    const current = sensorMap.get(slot.sensorId) || {
      sensorId: slot.sensorId,
      totalSlots: 0,
      occupiedSlots: 0,
      offlineSlots: 0,
      lastReading: 0,
      status: "offline" as HealthStatus,
    };

    current.totalSlots += 1;
    if (slot.status === "occupied") {
      current.occupiedSlots += 1;
    }
    if (slot.status === "offline") {
      current.offlineSlots += 1;
    }
    current.lastReading = Math.max(current.lastReading, slot.lastUpdate);
    current.status = deriveHealthStatus(current.totalSlots, current.offlineSlots);

    sensorMap.set(slot.sensorId, current);
  }

  return Array.from(sensorMap.values()).sort((a, b) => a.sensorId.localeCompare(b.sensorId));
}

function buildActivityBuckets(events: ActivityEvent[], hours = 6): ActivityBucket[] {
  const oneHourMs = 60 * 60 * 1000;
  const now = Date.now();
  const start = now - (hours - 1) * oneHourMs;

  const buckets: ActivityBucket[] = Array.from({ length: hours }, (_, index) => {
    const bucketTs = start + index * oneHourMs;
    return {
      label: `${new Date(bucketTs).toISOString().slice(11, 13)}:00`,
      entries: 0,
      exits: 0,
      total: 0,
    };
  });

  for (const event of events) {
    if (event.timestamp < start) {
      continue;
    }

    const index = Math.min(
      hours - 1,
      Math.floor((event.timestamp - start) / oneHourMs)
    );

    if (index < 0 || index >= buckets.length) {
      continue;
    }

    const bucket = buckets[index];
    if (event.type === "entry") {
      bucket.entries += 1;
    } else {
      bucket.exits += 1;
    }
    bucket.total += 1;
  }

  return buckets;
}

export function AdminClient() {
  const dashboardFetch = useCallback(() => fetchDashboardData(), []);
  const activityFetch = useCallback(() => fetchActivityEvents(40), []);

  const {
    data: dashboardData,
    loading,
    refreshing,
    error,
    retry,
  } = usePolling(dashboardFetch, 5000);

  const {
    data: activityData,
    error: activityError,
    retry: retryActivity,
  } = usePolling<ActivityEvent[]>(activityFetch, 7000);

  const sensorRows = useMemo(
    () => buildSensorRows(dashboardData?.slots || []),
    [dashboardData?.slots]
  );

  const totals = useMemo(() => {
    const totalSensors = sensorRows.length;
    const offlineSensors = sensorRows.filter((row) => row.status === "offline").length;
    const degradedSensors = sensorRows.filter((row) => row.status === "degraded").length;

    return { totalSensors, offlineSensors, degradedSensors };
  }, [sensorRows]);

  const recentEvents = useMemo(() => activityData ?? [], [activityData]);

  const activityBuckets = useMemo(
    () => buildActivityBuckets(recentEvents, 6),
    [recentEvents]
  );

  const analytics = useMemo(() => {
    const peakVolume = activityBuckets.reduce(
      (maxVolume, bucket) => Math.max(maxVolume, bucket.total),
      0
    );
    const entryCount = activityBuckets.reduce(
      (sum, bucket) => sum + bucket.entries,
      0
    );
    const exitCount = activityBuckets.reduce((sum, bucket) => sum + bucket.exits, 0);

    const slotFrequency = new Map<string, number>();
    for (const event of recentEvents) {
      slotFrequency.set(event.slot, (slotFrequency.get(event.slot) || 0) + 1);
    }

    let busiestSlot = "--";
    let busiestSlotCount = 0;
    for (const [slot, count] of slotFrequency.entries()) {
      if (count > busiestSlotCount) {
        busiestSlot = slot;
        busiestSlotCount = count;
      }
    }

    const latestEventTime = recentEvents.reduce(
      (latest, event) => Math.max(latest, event.timestamp),
      0
    );

    return {
      peakVolume,
      entryCount,
      exitCount,
      netFlow: entryCount - exitCount,
      busiestSlot,
      busiestSlotCount,
      latestEventTime,
      occupancyRate: dashboardData?.stats.occupancyRate || 0,
      offlineSensors: totals.offlineSensors,
      degradedSensors: totals.degradedSensors,
    };
  }, [activityBuckets, dashboardData?.stats.occupancyRate, recentEvents, totals.degradedSensors, totals.offlineSensors]);

  return (
    <ProtectedRoute requireRole="admin">
      <AppShell>
          <PageHeader
            title="Admin Control"
            subtitle="Sensor fleet health and live operational analytics"
          >
            <div className="flex flex-wrap items-center gap-4 border border-[var(--border-default)] bg-[var(--bg-secondary)] px-4 py-2">
              <div className="flex items-center gap-2">
                <span className="label-quiet">Sensors</span>
                <span className="font-mono text-lg font-bold text-[var(--text-primary)]">
                  {totals.totalSensors.toString().padStart(2, "0")}
                </span>
              </div>
              <div className="h-6 w-px bg-[var(--border-default)]" />
              <div className="flex items-center gap-2">
                <span className="label-quiet">Degraded</span>
                <span className="font-mono text-lg font-bold text-[var(--warning)]">
                  {totals.degradedSensors.toString().padStart(2, "0")}
                </span>
              </div>
              <div className="h-6 w-px bg-[var(--border-default)]" />
              <div className="flex items-center gap-2">
                <span className="label-quiet">Offline</span>
                <span className="font-mono text-lg font-bold text-[var(--occupied)]">
                  {totals.offlineSensors.toString().padStart(2, "0")}
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

          {(error || activityError) && (
            <PollingNotice
              message={error || activityError || "Data refresh warning"}
              actions={[
                { label: "Retry Health", onClick: retry },
                { label: "Retry Activity", onClick: retryActivity },
              ]}
            />
          )}

          <section className="mb-8" aria-label="Sensor health table">
            <SectionHeader title="Sensor Health" count={sensorRows.length} />
            {loading && sensorRows.length === 0 ? (
              <div className="space-y-2">
                {[1, 2, 3].map((item) => (
                  <div key={item} className="skeleton h-12 border border-[var(--border-subtle)]" />
                ))}
              </div>
            ) : sensorRows.length > 0 ? (
              <div className="space-y-3">
                <div className="hidden overflow-hidden border border-[var(--border-default)] bg-[var(--bg-secondary)] md:block">
                  <div className="grid grid-cols-5 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-3 font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    <span>Sensor</span>
                    <span className="text-center">Slots</span>
                    <span className="text-center">Occupied</span>
                    <span className="text-center">Last Read</span>
                    <span className="text-center">Status</span>
                  </div>
                  {sensorRows.map((row) => (
                    <div key={row.sensorId} className="grid grid-cols-5 border-b border-[var(--border-subtle)] px-4 py-3 font-mono text-sm last:border-b-0">
                      <span className="font-semibold text-[var(--text-primary)]">{row.sensorId}</span>
                      <span className="text-center text-[var(--text-secondary)]">{row.totalSlots}</span>
                      <span className="text-center text-[var(--warning)]">{row.occupiedSlots}</span>
                      <span className="text-center text-[var(--accent)]">{formatUtcTime(row.lastReading)} UTC</span>
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
                    <article
                      key={row.sensorId}
                      className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-3"
                    >
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
                        <div className="col-span-2 rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                          <dt className="label-quiet">Last Read (UTC)</dt>
                          <dd className="font-mono text-[var(--accent)]">{formatUtcTime(row.lastReading)}</dd>
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
                Event Volume (Last 6h)
              </h2>
              <p className="mt-2 text-sm text-[var(--text-muted)]">
                Entry and exit volume by hour (UTC) from the live event stream.
              </p>
              {recentEvents.length > 0 ? (
                <div className="mt-4 border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-3">
                  <div className="flex h-32 items-end gap-2">
                    {activityBuckets.map((bucket) => {
                      const percent = analytics.peakVolume > 0
                        ? (bucket.total / analytics.peakVolume) * 100
                        : 0;
                      const barHeight = Math.max(percent, bucket.total > 0 ? 8 : 2);

                      return (
                        <div key={bucket.label} className="flex flex-1 flex-col items-center gap-1">
                          <div className="flex h-24 w-full items-end rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-primary)] px-1 py-1">
                            <div
                              className="w-full rounded-[1px] bg-[var(--accent)]/75"
                              style={{ height: `${barHeight}%` }}
                              aria-label={`${bucket.label}: ${bucket.total} events`}
                            />
                          </div>
                          <span className="font-mono text-[10px] text-[var(--text-muted)]">
                            {bucket.label.slice(0, 2)}
                          </span>
                          <span className="font-mono text-[10px] text-[var(--text-secondary)]">
                            {bucket.total}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-2 py-1.5">
                      <span className="label-quiet">Entries</span>
                      <div className="font-mono text-[var(--vacant)]">{analytics.entryCount}</div>
                    </div>
                    <div className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-2 py-1.5">
                      <span className="label-quiet">Exits</span>
                      <div className="font-mono text-[var(--occupied)]">{analytics.exitCount}</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-4 border border-dashed border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-6 text-xs text-[var(--text-muted)]">
                  Waiting for events. Keep simulator or sensors running to populate this chart.
                </div>
              )}
            </article>

            <article className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4">
              <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                Operational Signals
              </h2>
              <p className="mt-2 text-sm text-[var(--text-muted)]">
                Live indicators derived from current telemetry and recent activity.
              </p>
              <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                  <dt className="label-quiet">Occupancy</dt>
                  <dd className="font-mono text-[var(--accent)]">{analytics.occupancyRate}%</dd>
                </div>
                <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                  <dt className="label-quiet">Net Flow</dt>
                  <dd className={`font-mono ${analytics.netFlow >= 0 ? "text-[var(--warning)]" : "text-[var(--vacant)]"}`}>
                    {analytics.netFlow >= 0 ? "+" : ""}
                    {analytics.netFlow}
                  </dd>
                </div>
                <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                  <dt className="label-quiet">Busiest Slot</dt>
                  <dd className="font-mono text-[var(--text-primary)]">
                    {analytics.busiestSlot} {analytics.busiestSlotCount > 0 ? `(${analytics.busiestSlotCount})` : ""}
                  </dd>
                </div>
                <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                  <dt className="label-quiet">Last Event</dt>
                  <dd className="font-mono text-[var(--accent)]">{formatUtcTimeMs(analytics.latestEventTime)} UTC</dd>
                </div>
                <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                  <dt className="label-quiet">Offline Sensors</dt>
                  <dd className="font-mono text-[var(--occupied)]">{analytics.offlineSensors}</dd>
                </div>
                <div className="border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2">
                  <dt className="label-quiet">Degraded Sensors</dt>
                  <dd className="font-mono text-[var(--warning)]">{analytics.degradedSensors}</dd>
                </div>
              </dl>
              <div className="mt-4 max-h-40 space-y-2 overflow-y-auto">
                {recentEvents.slice(0, 8).map((event) => (
                  <div key={event.id} className="flex items-center justify-between border border-[var(--border-subtle)] px-3 py-2 text-xs">
                    <span className="font-mono text-[var(--text-primary)]">{event.slot}</span>
                    <span className="font-display uppercase text-[var(--text-muted)]">{event.type}</span>
                    <span className="font-mono text-[var(--accent)]">{new Date(event.timestamp).toISOString().slice(11, 19)}</span>
                  </div>
                ))}
                {recentEvents.length === 0 && (
                  <div className="border border-dashed border-[var(--border-subtle)] px-3 py-3 text-xs text-[var(--text-muted)]">
                    No events available yet.
                  </div>
                )}
              </div>
            </article>
          </section>
      </AppShell>
    </ProtectedRoute>
  );
}
