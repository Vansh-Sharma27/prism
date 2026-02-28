import { Navbar } from "@/components/Navbar";
import { PageHeader } from "@/components/PageHeader";
import { mockEvents } from "@/lib/mock-data";
import { formatTime, formatDate, formatRelativeTime } from "@/lib/format";
import { ArrowDownRight, ArrowUpRight, Clock } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Activity Log | PRISM",
};

export default function ActivityPage() {
  const entryCount = mockEvents.filter((e) => e.type === "entry").length;
  const exitCount = mockEvents.filter((e) => e.type === "exit").length;

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <Navbar />

      <main id="main-content" className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <PageHeader
          title="Activity Log"
          subtitle="Real-time event stream from all sensors"
        >
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-subtle)]">
              <ArrowDownRight size={14} className="text-[var(--occupied)]" />
              <span className="font-mono text-sm text-[var(--occupied)] tabular-nums">{entryCount}</span>
              <span className="label-quiet">entries</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-subtle)]">
              <ArrowUpRight size={14} className="text-[var(--vacant)]" />
              <span className="font-mono text-sm text-[var(--vacant)] tabular-nums">{exitCount}</span>
              <span className="label-quiet">exits</span>
            </div>
          </div>
        </PageHeader>

        {/* Desktop Table - hidden on mobile */}
        <div className="hidden md:block border border-[var(--border-default)] bg-[var(--bg-secondary)]" role="table" aria-label="Activity events">
          {/* Table Header */}
          <div role="rowgroup">
            <div className="grid grid-cols-12 gap-4 px-4 py-3 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)]" role="row">
            <div className="col-span-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display" role="columnheader">
              Time
            </div>
            <div className="col-span-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display" role="columnheader">
              Event
            </div>
            <div className="col-span-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display" role="columnheader">
              Slot
            </div>
            <div className="col-span-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display" role="columnheader">
              Location
            </div>
            <div className="col-span-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display text-right" role="columnheader">
              Date
            </div>
          </div>
          </div>

          {/* Table Body */}
          <div className="divide-y divide-[var(--border-subtle)]" role="rowgroup">
            {mockEvents.map((event, index) => (
              <div
                key={event.id}
                className="grid grid-cols-12 gap-4 px-4 py-3 transition-colors hover:bg-[var(--bg-tertiary)] animate-slide-in"
                style={{ animationDelay: `${Math.min(index * 50, 300)}ms` }}
                role="row"
              >
                <div className="col-span-2 font-mono text-sm text-[var(--accent)] tabular-nums" role="cell">
                  {formatTime(event.timestamp)}
                </div>
                <div className="col-span-2 flex items-center gap-2" role="cell">
                  <div
                    className={`flex h-6 w-6 items-center justify-center border ${
                      event.type === "entry"
                        ? "border-[var(--occupied)]/40 bg-[var(--occupied)]/10"
                        : "border-[var(--vacant)]/40 bg-[var(--vacant)]/10"
                    }`}
                  >
                    {event.type === "entry" ? (
                      <ArrowDownRight size={14} className="text-[var(--occupied)]" />
                    ) : (
                      <ArrowUpRight size={14} className="text-[var(--vacant)]" />
                    )}
                  </div>
                  <span
                    className={`text-xs font-semibold uppercase tracking-wider font-display ${
                      event.type === "entry"
                        ? "text-[var(--occupied)]"
                        : "text-[var(--vacant)]"
                    }`}
                  >
                    {event.type}
                  </span>
                </div>
                <div className="col-span-2 font-mono text-sm font-semibold text-[var(--text-primary)]" role="cell">
                  {event.slot}
                </div>
                <div className="col-span-3 text-sm text-[var(--text-secondary)]" role="cell">
                  {event.lot}
                </div>
                <div className="col-span-3 font-mono text-sm text-[var(--text-muted)] tabular-nums text-right" role="cell">
                  {formatDate(event.timestamp)}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-[var(--border-default)] bg-[var(--bg-tertiary)] flex items-center justify-between">
            <span className="font-mono text-xs text-[var(--text-muted)]">
              {mockEvents.length} events
            </span>
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--vacant)] opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--vacant)]"></span>
              </span>
              <span className="font-mono text-xs text-[var(--vacant)]">
                LIVE
              </span>
            </div>
          </div>
        </div>

        {/* Mobile Card Layout - visible only on mobile */}
        <div className="md:hidden space-y-2">
          {mockEvents.map((event, index) => (
            <div
              key={event.id}
              className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-3 animate-scale-in"
              style={{ animationDelay: `${Math.min(index * 40, 300)}ms` }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`flex h-7 w-7 items-center justify-center border ${
                      event.type === "entry"
                        ? "border-[var(--occupied)]/40 bg-[var(--occupied)]/10"
                        : "border-[var(--vacant)]/40 bg-[var(--vacant)]/10"
                    }`}
                  >
                    {event.type === "entry" ? (
                      <ArrowDownRight size={14} className="text-[var(--occupied)]" />
                    ) : (
                      <ArrowUpRight size={14} className="text-[var(--vacant)]" />
                    )}
                  </div>
                  <div>
                    <span
                      className={`text-xs font-semibold uppercase tracking-wider font-display ${
                        event.type === "entry"
                          ? "text-[var(--occupied)]"
                          : "text-[var(--vacant)]"
                      }`}
                    >
                      {event.type}
                    </span>
                    <span className="ml-2 font-mono text-sm font-semibold text-[var(--text-primary)]">
                      {event.slot}
                    </span>
                  </div>
                </div>
                <span className="font-mono text-xs text-[var(--text-muted)]">
                  {formatRelativeTime(event.timestamp)}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
                <span>{event.lot}</span>
                <span className="font-mono tabular-nums text-[var(--accent)]">
                  {formatTime(event.timestamp)}
                </span>
              </div>
            </div>
          ))}

          {/* Mobile footer */}
          <div className="flex items-center justify-between pt-3">
            <span className="font-mono text-xs text-[var(--text-muted)]">
              {mockEvents.length} events
            </span>
            <div className="flex items-center gap-2">
              <Clock size={12} className="text-[var(--vacant)]" />
              <span className="font-mono text-xs text-[var(--vacant)]">Live</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
