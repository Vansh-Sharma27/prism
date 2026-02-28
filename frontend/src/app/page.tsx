import { Navbar } from "@/components/Navbar";
import { StatsGrid } from "@/components/StatsGrid";
import { LotCard } from "@/components/LotCard";
import { SlotCard } from "@/components/SlotCard";
import { PageHeader, SectionHeader } from "@/components/PageHeader";
import { mockLots, mockSlots, mockStats } from "@/lib/mock-data";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <Navbar />

      <main id="main-content" className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <PageHeader
          title="Control Dashboard"
          subtitle="Real-time parking slot monitoring — GLA University Campus"
        >
          {/* Last sync timestamp */}
          <div className="flex items-center gap-2 px-3 py-1.5 border border-[var(--border-default)] bg-[var(--bg-secondary)]">
            <span className="font-mono text-xs text-[var(--text-muted)]">LAST SYNC</span>
            <span className="font-mono text-sm font-bold text-[var(--accent)] tabular-nums ml-1">
              {new Date(mockStats.lastUpdate * 1000).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        </PageHeader>

        {/* Stats Grid */}
        <section className="mb-8" aria-label="System statistics">
          <StatsGrid stats={mockStats} />
        </section>

        {/* Parking Lots Section */}
        <section className="mb-8" aria-label="Parking lots overview">
          <SectionHeader title="Parking Lots" count={mockLots.length} />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="list">
            {mockLots.map((lot, index) => (
              <div key={lot.id} role="listitem">
                <LotCard lot={lot} index={index} />
              </div>
            ))}
          </div>
        </section>

        {/* Live Slot Grid */}
        <section aria-label="Live slot monitor">
          <SectionHeader
            title="Live Slot Monitor"
            subtitle="Main Building"
          />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" role="list">
            {mockSlots.map((slot, index) => (
              <div key={slot.id} role="listitem">
                <SlotCard slot={slot} index={index} />
              </div>
            ))}
          </div>
        </section>

        {/* System Status Footer */}
        <footer className="mt-12 border-t border-[var(--border-default)] pt-6" aria-label="System connection status">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-6" role="status" aria-live="polite">
              <StatusIndicator label="MQTT" status="online" />
              <StatusIndicator label="Database" status="online" />
              <StatusIndicator label="Sensors" status="warning" detail="5/6" />
            </div>
            <p className="font-mono text-xs text-[var(--text-muted)]">
              PRISM v1.0 | GLA University
            </p>
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
      <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display">
        {label}
      </span>
      <span className="sr-only">{status}</span>
      {detail && (
        <span className={`font-mono text-xs ${config.text}`}>{detail}</span>
      )}
    </div>
  );
}
