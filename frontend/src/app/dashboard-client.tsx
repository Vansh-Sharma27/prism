"use client";

import { useCallback } from "react";
import { Navbar } from "@/components/Navbar";
import { StatsGrid } from "@/components/StatsGrid";
import { LotCard } from "@/components/LotCard";
import { SlotCard } from "@/components/SlotCard";
import { PageHeader, SectionHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { fetchDashboardData } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

const EMPTY_STATS = {
  totalLots: 0,
  totalSlots: 0,
  occupiedSlots: 0,
  vacantSlots: 0,
  offlineSlots: 0,
  occupancyRate: 0,
  lastUpdate: Math.floor(Date.now() / 1000),
};

export function DashboardClient() {
  const fetchFn = useCallback(() => fetchDashboardData(), []);
  const { data, loading, error } = usePolling(fetchFn, 5000);

  const lots = data?.lots || [];
  const slots = data?.slots || [];
  const stats = data?.stats || EMPTY_STATS;
  const syncedAt = new Date(stats.lastUpdate * 1000).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
  });

  const sensorDetail = stats.totalSlots > 0
    ? `${Math.max(stats.totalSlots - stats.offlineSlots, 0)}/${stats.totalSlots}`
    : "0/0";

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <Navbar />

      <main id="main-content" className="mx-auto max-w-7xl px-4 pb-16 pt-24 sm:px-6">
        <PageHeader
          title="Control Dashboard"
          subtitle="Real-time parking slot monitoring - GLA University Campus"
        >
          <div className="flex items-center gap-2 border border-[var(--border-default)] bg-[var(--bg-secondary)] px-3 py-1.5">
            <span className="font-mono text-xs text-[var(--text-muted)]">LAST SYNC</span>
            <span className="ml-1 font-mono text-sm font-bold tabular-nums text-[var(--accent)]">{syncedAt}</span>
          </div>
        </PageHeader>

        {error && (
          <div className="mb-6 border border-[var(--warning)]/40 bg-[var(--warning)]/10 px-4 py-3 text-sm text-[var(--warning)]">
            API poll warning: {error}
          </div>
        )}

        <section className="mb-8" aria-label="System statistics">
          <StatsGrid stats={stats} />
        </section>

        <section className="mb-8" aria-label="Parking lots overview">
          <SectionHeader title="Parking Lots" count={lots.length} />
          {loading && lots.length === 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton h-44 border border-[var(--border-subtle)]" />
              ))}
            </div>
          ) : lots.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="list">
              {lots.map((lot, index) => (
                <div key={lot.id} role="listitem">
                  <LotCard lot={lot} index={index} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              variant="no-data"
              title="No Lots Found"
              description="Create lots and slots in backend to begin live monitoring."
            />
          )}
        </section>

        <section aria-label="Live slot monitor">
          <SectionHeader title="Live Slot Monitor" subtitle="All Lots" />
          {slots.length > 0 ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" role="list">
              {slots.map((slot, index) => (
                <div key={slot.id} role="listitem">
                  <SlotCard slot={slot} index={index} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              variant="no-results"
              title="No Slot Telemetry"
              description="Start simulator or firmware publishing to populate live slots."
            />
          )}
        </section>

        <footer className="mt-12 border-t border-[var(--border-default)] pt-6" aria-label="System connection status">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-6" role="status" aria-live="polite">
              <StatusIndicator label="MQTT" status={error ? "warning" : "online"} />
              <StatusIndicator label="Database" status={error ? "warning" : "online"} />
              <StatusIndicator
                label="Sensors"
                status={stats.offlineSlots > 0 ? "warning" : "online"}
                detail={sensorDetail}
              />
            </div>
            <p className="font-mono text-xs text-[var(--text-muted)]">PRISM v1.0 | GLA University</p>
          </div>
        </footer>
      </main>
    </div>
  );
}

function StatusIndicator({
  label,
  status,
  detail,
}: {
  label: string;
  status: "online" | "offline" | "warning";
  detail?: string;
}) {
  const colors = {
    online: { dot: "status-dot-vacant", text: "text-[var(--vacant)]" },
    offline: { dot: "status-dot-occupied", text: "text-[var(--occupied)]" },
    warning: { dot: "bg-[var(--warning)]", text: "text-[var(--warning)]" },
  };

  const config = colors[status];

  return (
    <div className="flex items-center gap-2">
      <span className={`status-dot ${config.dot}`} aria-hidden="true" />
      <span className="font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
        {label}
      </span>
      <span className="sr-only">{status}</span>
      {detail && <span className={`font-mono text-xs ${config.text}`}>{detail}</span>}
    </div>
  );
}
