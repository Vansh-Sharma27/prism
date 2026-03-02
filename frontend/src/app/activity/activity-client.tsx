"use client";

import { useCallback } from "react";
import { Navbar } from "@/components/Navbar";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { fetchActivityEvents } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";
import { formatTime, formatDate, formatRelativeTime } from "@/lib/format";
import { ArrowDownRight, ArrowUpRight, Clock } from "lucide-react";

export function ActivityClient() {
  const fetchFn = useCallback(() => fetchActivityEvents(), []);
  const { data, error, retry, refreshing, loading } = usePolling(fetchFn, 5000);

  const events = data || [];
  const entryCount = events.filter((event) => event.type === "entry").length;
  const exitCount = events.filter((event) => event.type === "exit").length;

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
        <Navbar />

        <main id="main-content" className="mx-auto max-w-7xl px-4 pb-16 pt-24 sm:px-6">
          <PageHeader title="Activity Log" subtitle="Real-time event stream from all sensors">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-3 py-1.5">
                <ArrowDownRight size={14} className="text-[var(--occupied)]" />
                <span className="font-mono text-sm tabular-nums text-[var(--occupied)]">{entryCount}</span>
                <span className="label-quiet">entries</span>
              </div>
              <div className="flex items-center gap-2 border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-3 py-1.5">
                <ArrowUpRight size={14} className="text-[var(--vacant)]" />
                <span className="font-mono text-sm tabular-nums text-[var(--vacant)]">{exitCount}</span>
                <span className="label-quiet">exits</span>
              </div>
              {refreshing && (
                <span className="font-mono text-xs text-[var(--accent)]">SYNC...</span>
              )}
            </div>
          </PageHeader>

          {error && (
            <div className="mb-6 border border-[var(--warning)]/40 bg-[var(--warning)]/10 px-4 py-3 text-sm text-[var(--warning)]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span>API poll warning: {error}</span>
                <button
                  type="button"
                  onClick={retry}
                  className="border border-[var(--warning)]/50 px-3 py-1 text-xs font-display font-semibold uppercase tracking-wider transition-colors hover:bg-[var(--warning)]/15"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {loading && events.length === 0 ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((item) => (
                <div key={item} className="skeleton h-14 border border-[var(--border-subtle)]" />
              ))}
            </div>
          ) : events.length === 0 ? (
            <EmptyState
              variant="no-results"
              title="No Activity Yet"
              description="Events will appear when slot occupancy changes are detected."
            />
          ) : (
            <>
              <div className="hidden border border-[var(--border-default)] bg-[var(--bg-secondary)] md:block" role="table" aria-label="Activity events">
                <div role="rowgroup">
                  <div className="grid grid-cols-12 gap-4 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-3" role="row">
                    <div className="col-span-2 font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]" role="columnheader">Time</div>
                    <div className="col-span-2 font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]" role="columnheader">Event</div>
                    <div className="col-span-2 font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]" role="columnheader">Slot</div>
                    <div className="col-span-3 font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]" role="columnheader">Location</div>
                    <div className="col-span-3 text-right font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]" role="columnheader">Date</div>
                  </div>
                </div>

                <div className="divide-y divide-[var(--border-subtle)]" role="rowgroup">
                  {events.map((event, index) => (
                    <div
                      key={event.id}
                      className="grid grid-cols-12 gap-4 px-4 py-3 transition-colors hover:bg-[var(--bg-tertiary)] animate-slide-in"
                      style={{ animationDelay: `${Math.min(index * 50, 300)}ms` }}
                      role="row"
                    >
                      <div className="col-span-2 font-mono text-sm tabular-nums text-[var(--accent)]" role="cell">{formatTime(event.timestamp)}</div>
                      <div className="col-span-2 flex items-center gap-2" role="cell">
                        <div className={`flex h-6 w-6 items-center justify-center border ${
                          event.type === "entry"
                            ? "border-[var(--occupied)]/40 bg-[var(--occupied)]/10"
                            : "border-[var(--vacant)]/40 bg-[var(--vacant)]/10"
                        }`}>
                          {event.type === "entry" ? (
                            <ArrowDownRight size={14} className="text-[var(--occupied)]" />
                          ) : (
                            <ArrowUpRight size={14} className="text-[var(--vacant)]" />
                          )}
                        </div>
                        <span className={`font-display text-xs font-semibold uppercase tracking-wider ${
                          event.type === "entry" ? "text-[var(--occupied)]" : "text-[var(--vacant)]"
                        }`}>
                          {event.type}
                        </span>
                      </div>
                      <div className="col-span-2 font-mono text-sm font-semibold text-[var(--text-primary)]" role="cell">{event.slot}</div>
                      <div className="col-span-3 text-sm text-[var(--text-secondary)]" role="cell">{event.lot}</div>
                      <div className="col-span-3 text-right font-mono text-sm tabular-nums text-[var(--text-muted)]" role="cell">{formatDate(event.timestamp)}</div>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between border-t border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-3">
                  <span className="font-mono text-xs text-[var(--text-muted)]">{events.length} events</span>
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--vacant)] opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--vacant)]" />
                    </span>
                    <span className="font-mono text-xs text-[var(--vacant)]">LIVE</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2 md:hidden">
                {events.map((event, index) => (
                  <div
                    key={event.id}
                    className="animate-scale-in border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-3"
                    style={{ animationDelay: `${Math.min(index * 40, 300)}ms` }}
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`flex h-7 w-7 items-center justify-center border ${
                          event.type === "entry"
                            ? "border-[var(--occupied)]/40 bg-[var(--occupied)]/10"
                            : "border-[var(--vacant)]/40 bg-[var(--vacant)]/10"
                        }`}>
                          {event.type === "entry" ? (
                            <ArrowDownRight size={14} className="text-[var(--occupied)]" />
                          ) : (
                            <ArrowUpRight size={14} className="text-[var(--vacant)]" />
                          )}
                        </div>
                        <div>
                          <span className={`font-display text-xs font-semibold uppercase tracking-wider ${
                            event.type === "entry" ? "text-[var(--occupied)]" : "text-[var(--vacant)]"
                          }`}>
                            {event.type}
                          </span>
                          <span className="ml-2 font-mono text-sm font-semibold text-[var(--text-primary)]">{event.slot}</span>
                        </div>
                      </div>
                      <span className="font-mono text-xs text-[var(--text-muted)]">{formatRelativeTime(event.timestamp)}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
                      <span>{event.lot}</span>
                      <span className="font-mono tabular-nums text-[var(--accent)]">{formatTime(event.timestamp)}</span>
                    </div>
                  </div>
                ))}

                <div className="flex items-center justify-between pt-3">
                  <span className="font-mono text-xs text-[var(--text-muted)]">{events.length} events</span>
                  <div className="flex items-center gap-2">
                    <Clock size={12} className="text-[var(--vacant)]" />
                    <span className="font-mono text-xs text-[var(--vacant)]">Live</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
