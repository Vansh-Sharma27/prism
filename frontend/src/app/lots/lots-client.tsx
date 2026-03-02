"use client";

import { useCallback } from "react";
import { Navbar } from "@/components/Navbar";
import { LotCard } from "@/components/LotCard";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { fetchLots } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

export function LotsClient() {
  const fetchFn = useCallback(() => fetchLots(), []);
  const { data, loading, error, retry, refreshing } = usePolling(fetchFn, 8000);

  const lots = data || [];
  const totalSlots = lots.reduce((acc, lot) => acc + lot.totalSlots, 0);
  const totalOccupied = lots.reduce((acc, lot) => acc + lot.occupiedSlots, 0);
  const loadPercent = totalSlots > 0 ? Math.round((totalOccupied / totalSlots) * 100) : 0;

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
        <Navbar />

        <main id="main-content" className="mx-auto max-w-7xl px-4 pb-16 pt-24 sm:px-6">
          <PageHeader title="Parking Lots" subtitle="All registered parking locations">
            <div className="flex flex-wrap items-center gap-4 border border-[var(--border-default)] bg-[var(--bg-secondary)] px-4 py-2 sm:gap-6">
              <div className="flex items-center gap-2">
                <span className="label-quiet">Lots</span>
                <span className="font-mono text-lg font-bold text-[var(--accent)]">
                  {lots.length.toString().padStart(2, "0")}
                </span>
              </div>
              <div className="h-6 w-px bg-[var(--border-default)]" />
              <div className="flex items-center gap-2">
                <span className="label-quiet">Total</span>
                <span className="font-mono text-lg font-bold text-[var(--text-primary)]">
                  {totalSlots.toString().padStart(2, "0")}
                </span>
              </div>
              <div className="h-6 w-px bg-[var(--border-default)]" />
              <div className="flex items-center gap-2">
                <span className="label-quiet">Load</span>
                <span className="font-mono text-lg font-bold text-[var(--warning)]">{loadPercent}%</span>
              </div>
              {refreshing && (
                <>
                  <div className="h-6 w-px bg-[var(--border-default)]" />
                  <span className="font-mono text-xs text-[var(--accent)]">SYNC...</span>
                </>
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
              title="No Lots Configured"
              description="Create a parking lot and slots in backend to begin monitoring."
            />
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
