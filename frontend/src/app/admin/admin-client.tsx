"use client";

import { useCallback, useMemo } from "react";
import { Navbar } from "@/components/Navbar";
import { PageHeader, SectionHeader } from "@/components/PageHeader";
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

function formatUtcTime(ts: number): string {
  if (!ts) {
    return "--:--";
  }
  return new Date(ts * 1000).toISOString().slice(11, 16);
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

  const recentEvents = activityData || [];

  return (
    <ProtectedRoute requireRole="admin">
      <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
        <Navbar />

        <main id="main-content" className="mx-auto max-w-7xl px-4 pb-16 pt-24 sm:px-6">
          <PageHeader
            title="Admin Control"
            subtitle="Sensor fleet health and analytics scaffolding"
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
            <div className="mb-6 border border-[var(--warning)]/40 bg-[var(--warning)]/10 px-4 py-3 text-sm text-[var(--warning)]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span>{error || activityError}</span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={retry}
                    className="border border-[var(--warning)]/50 px-3 py-1 text-xs font-display font-semibold uppercase tracking-wider transition-colors hover:bg-[var(--warning)]/15"
                  >
                    Retry Health
                  </button>
                  <button
                    type="button"
                    onClick={retryActivity}
                    className="border border-[var(--warning)]/50 px-3 py-1 text-xs font-display font-semibold uppercase tracking-wider transition-colors hover:bg-[var(--warning)]/15"
                  >
                    Retry Activity
                  </button>
                </div>
              </div>
            </div>
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
              <div className="overflow-hidden border border-[var(--border-default)] bg-[var(--bg-secondary)]">
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
            ) : (
              <div className="border border-[var(--border-default)] bg-[var(--bg-secondary)] px-4 py-6 text-sm text-[var(--text-muted)]">
                No sensor telemetry yet. Start simulator or firmware nodes.
              </div>
            )}
          </section>

          <section className="grid gap-4 lg:grid-cols-2" aria-label="Analytics placeholders">
            <article className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4">
              <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                Occupancy Trend (Placeholder)
              </h2>
              <p className="mt-2 text-sm text-[var(--text-muted)]">
                Chart module will plot lot occupancy against timestamps and sensor outage windows.
              </p>
              <div className="mt-4 h-40 border border-dashed border-[var(--border-subtle)] bg-[var(--bg-tertiary)]" />
            </article>

            <article className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-4">
              <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                Recent Events (Placeholder)
              </h2>
              <p className="mt-2 text-sm text-[var(--text-muted)]">
                Last {recentEvents.length} activity entries for future anomaly-detection overlays.
              </p>
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
        </main>
      </div>
    </ProtectedRoute>
  );
}
