import { Navbar } from "@/components/Navbar";
import { LotCard } from "@/components/LotCard";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { mockLots } from "@/lib/mock-data";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Parking Lots | PRISM",
};

export default function LotsPage() {
  const totalSlots = mockLots.reduce((acc, lot) => acc + lot.totalSlots, 0);
  const totalOccupied = mockLots.reduce((acc, lot) => acc + lot.occupiedSlots, 0);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <Navbar />

      <main id="main-content" className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <PageHeader
          title="Parking Lots"
          subtitle="All registered parking locations"
        >
          <div className="flex flex-wrap items-center gap-4 sm:gap-6 px-4 py-2 border border-[var(--border-default)] bg-[var(--bg-secondary)]">
            <div className="flex items-center gap-2">
              <span className="label-quiet">Lots</span>
              <span className="font-mono text-lg font-bold text-[var(--accent)]">
                {mockLots.length.toString().padStart(2, "0")}
              </span>
            </div>
            <div className="w-px h-6 bg-[var(--border-default)]" />
            <div className="flex items-center gap-2">
              <span className="label-quiet">Total</span>
              <span className="font-mono text-lg font-bold text-[var(--text-primary)]">
                {totalSlots.toString().padStart(2, "0")}
              </span>
            </div>
            <div className="w-px h-6 bg-[var(--border-default)]" />
            <div className="flex items-center gap-2">
              <span className="label-quiet">Load</span>
              <span className="font-mono text-lg font-bold text-[var(--warning)]">
                {Math.round((totalOccupied / totalSlots) * 100)}%
              </span>
            </div>
          </div>
        </PageHeader>

        {/* Lot Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="list">
          {mockLots.map((lot, index) => (
            <div key={lot.id} role="listitem">
              <LotCard lot={lot} index={index} />
            </div>
          ))}
        </div>

        {/* Empty State */}
        {mockLots.length === 0 && (
          <EmptyState
            variant="no-data"
            title="No Lots Configured"
            description="Add a parking lot to begin monitoring"
          />
        )}
      </main>
    </div>
  );
}
