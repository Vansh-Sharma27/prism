"use client";

import { useCallback } from "react";
import { AppShell } from "@/components/AppShell";
import { SlotCard } from "@/components/SlotCard";
import { SlotGrid } from "@/components/SlotGrid";
import { SectionHeader, StatCell } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { PollingNotice } from "@/components/PollingNotice";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { fetchLotDetailData } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";
import { ArrowLeft, MapPin } from "lucide-react";
import Link from "next/link";

interface LotDetailClientProps {
  lotId: string;
}

export function LotDetailClient({ lotId }: LotDetailClientProps) {
  const fetchFn = useCallback(() => fetchLotDetailData(lotId), [lotId]);
  const { data, loading, error, retry, refreshing } = usePolling(fetchFn, 5000);

  const lot = data?.lot || null;
  const slots = data?.slots || [];
  const zones = data?.zones || [];

  const occupiedCount = slots.filter((slot) => slot.status === "occupied").length;
  const offlineCount = slots.filter((slot) => slot.status === "offline").length;
  const vacantCount = Math.max(slots.length - occupiedCount - offlineCount, 0);
  const occupancyPercent = slots.length > 0 ? Math.round((occupiedCount / slots.length) * 100) : 0;

  const lotName = lot?.name || "Lot Details";
  const lotLocation = lot?.location || "Location unavailable";

  return (
    <ProtectedRoute>
      <AppShell>
          <nav aria-label="Breadcrumb" className="mb-4">
            <Link
              href="/lots"
              className="inline-flex items-center gap-2 font-display text-xs uppercase tracking-wider text-[var(--text-muted)] transition-colors hover:text-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <ArrowLeft size={14} />
              Back to Lots
            </Link>
          </nav>

          <div className="mb-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className="mb-2 flex items-center gap-3">
                  <div className="h-6 w-1.5 bg-[var(--accent)]" />
                  <h1 className="font-display text-3xl font-bold uppercase tracking-wider text-[var(--text-primary)]">{lotName}</h1>
                </div>
                <div className="ml-[18px] flex items-center gap-2 text-sm text-[var(--text-muted)]">
                  <MapPin size={14} />
                  <span>{lotLocation}</span>
                  <span className="mx-1 text-[var(--border-default)]">|</span>
                  <span className="font-mono text-[var(--accent)]">{lotId.toUpperCase()}</span>
                </div>
              </div>
            </div>
            <div className="divider-accent mt-4" />
          </div>

          {error && (
            <PollingNotice
              message={`API poll warning: ${error}`}
              actions={[{ label: "Retry", onClick: retry }]}
            />
          )}

          <div className="mb-6 border border-[var(--border-default)] bg-[var(--bg-secondary)]">
            <div className="grid grid-cols-2 divide-[var(--border-default)] divide-y sm:grid-cols-4 sm:divide-x sm:divide-y-0">
              <StatCell label="Total" value={slots.length} color="var(--text-primary)" />
              <StatCell label="Vacant" value={vacantCount} color="var(--vacant)" />
              <StatCell label="Occupied" value={occupiedCount} color="var(--occupied)" />
              <StatCell label="Load" value={`${occupancyPercent}%`} color={occupancyPercent > 70 ? "var(--warning)" : "var(--vacant)"} />
            </div>
            <div
              className="flex h-1.5 bg-[var(--bg-elevated)]"
              role="img"
              aria-label={`Slot distribution: ${vacantCount} vacant, ${occupiedCount} occupied, ${offlineCount} offline out of ${slots.length} total`}
            >
              <div className="h-full" style={{ width: `${slots.length > 0 ? (vacantCount / slots.length) * 100 : 0}%`, backgroundColor: "var(--vacant)" }} />
              <div className="h-full" style={{ width: `${slots.length > 0 ? (occupiedCount / slots.length) * 100 : 0}%`, backgroundColor: "var(--occupied)" }} />
              <div className="h-full" style={{ width: `${slots.length > 0 ? (offlineCount / slots.length) * 100 : 0}%`, backgroundColor: "var(--offline)" }} />
            </div>
            {refreshing && (
              <div className="border-t border-[var(--border-subtle)] px-4 py-2 text-right font-mono text-xs text-[var(--accent)]">
                SYNC...
              </div>
            )}
          </div>

          <section className="mb-8" aria-label="Zone-level breakdown">
            <SectionHeader title="Zone Breakdown" count={zones.length} />
            {zones.length > 0 ? (
              <div className="space-y-3">
                <div className="hidden overflow-hidden border border-[var(--border-default)] bg-[var(--bg-secondary)] md:block">
                  <div className="grid grid-cols-5 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-3 font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    <span>Zone</span>
                    <span className="text-center">Total</span>
                    <span className="text-center">Vacant</span>
                    <span className="text-center">Occupied</span>
                    <span className="text-center">Offline</span>
                  </div>
                  {zones.map((zone) => (
                    <div key={zone.id} className="grid grid-cols-5 border-b border-[var(--border-subtle)] px-4 py-3 font-mono text-sm last:border-b-0">
                      <span className="font-display font-semibold uppercase tracking-wider text-[var(--text-primary)]">{zone.name}</span>
                      <span className="text-center text-[var(--text-primary)]">{zone.total}</span>
                      <span className="text-center text-[var(--vacant)]">{zone.vacant}</span>
                      <span className="text-center text-[var(--occupied)]">{zone.occupied}</span>
                      <span className="text-center text-[var(--offline)]">{zone.offline}</span>
                    </div>
                  ))}
                </div>

                <div className="space-y-2 md:hidden">
                  {zones.map((zone) => (
                    <article
                      key={zone.id}
                      className="border border-[var(--border-default)] bg-[var(--bg-secondary)] p-3"
                    >
                      <h3 className="font-display text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                        {zone.name}
                      </h3>
                      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                        <div className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                          <dt className="label-quiet">Total</dt>
                          <dd className="font-mono text-[var(--text-primary)]">{zone.total}</dd>
                        </div>
                        <div className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                          <dt className="label-quiet">Vacant</dt>
                          <dd className="font-mono text-[var(--vacant)]">{zone.vacant}</dd>
                        </div>
                        <div className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                          <dt className="label-quiet">Occupied</dt>
                          <dd className="font-mono text-[var(--occupied)]">{zone.occupied}</dd>
                        </div>
                        <div className="rounded-sm border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2.5 py-2">
                          <dt className="label-quiet">Offline</dt>
                          <dd className="font-mono text-[var(--offline)]">{zone.offline}</dd>
                        </div>
                      </dl>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState
                variant="no-results"
                title="No Zone Mapping"
                description="Assign slots to zones to view zone-level occupancy breakdown."
              />
            )}
          </section>

          <section className="mb-8" aria-label="Slot status grid">
            <SectionHeader title="Slot Grid" count={slots.length} subtitle="Real-time" />
            {loading && slots.length === 0 ? (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                {[1, 2, 3, 4, 5, 6].map((item) => (
                  <div key={item} className="skeleton h-20 border border-[var(--border-subtle)]" />
                ))}
              </div>
            ) : slots.length > 0 ? (
              <SlotGrid slots={slots} />
            ) : (
              <EmptyState
                variant="no-data"
                title="No Slots Found"
                description="This lot does not have slot records yet in the backend."
              />
            )}
          </section>

          <section aria-label="Detailed slot cards">
            <SectionHeader title="Detailed Slots" count={slots.length} />
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
                title="No Live Telemetry"
                description="Start simulator or connected sensors to stream slot updates."
              />
            )}
          </section>
      </AppShell>
    </ProtectedRoute>
  );
}
