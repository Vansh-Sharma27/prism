"use client";

import { useCallback } from "react";
import { AppShell } from "@/components/AppShell";
import { LotCard } from "@/components/LotCard";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { PollingNotice } from "@/components/PollingNotice";
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
      <AppShell>
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
            <PollingNotice
              message={`API poll warning: ${error}`}
              actions={[{ label: "Retry", onClick: retry }]}
            />
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
      </AppShell>
    </ProtectedRoute>
  );
}
