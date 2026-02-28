import { Navbar } from "@/components/Navbar";
import { SlotCard } from "@/components/SlotCard";
import { PageHeader, SectionHeader } from "@/components/PageHeader";
import { StatCell } from "@/components/PageHeader";
import { mockSlots } from "@/lib/mock-data";
import { ArrowLeft, MapPin } from "lucide-react";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Lot Details | PRISM",
};

interface LotDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function LotDetailPage({ params }: LotDetailPageProps) {
  const { id } = await params;

  const vacantCount = mockSlots.filter((s) => s.status === "vacant").length;
  const occupiedCount = mockSlots.filter((s) => s.status === "occupied").length;
  const occupancyPercent = Math.round((occupiedCount / mockSlots.length) * 100);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <Navbar />

      <main id="main-content" className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="mb-4">
          <Link
            href="/lots"
            className="inline-flex items-center gap-2 text-xs uppercase tracking-wider text-[var(--text-muted)] transition-colors hover:text-[var(--accent)] font-display focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <ArrowLeft size={14} />
            Back to Lots
          </Link>
        </nav>

        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="h-6 w-1.5 bg-[var(--accent)]" />
                <h1 className="text-3xl font-bold uppercase tracking-wider text-[var(--text-primary)] font-display">
                  Main Building
                </h1>
              </div>
              <div className="ml-[18px] flex items-center gap-2 text-sm text-[var(--text-muted)]">
                <MapPin size={14} />
                <span>Block A, Ground Floor</span>
                <span className="mx-1 text-[var(--border-default)]">|</span>
                <span className="font-mono text-[var(--accent)]">{id.toUpperCase()}</span>
              </div>
            </div>
          </div>
          <div className="divider-accent mt-4" />
        </div>

        {/* Stats Bar - responsive */}
        <div className="mb-6 border border-[var(--border-default)] bg-[var(--bg-secondary)]">
          <div className="grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-[var(--border-default)]">
            <StatCell label="Total" value={mockSlots.length} color="var(--text-primary)" />
            <StatCell label="Vacant" value={vacantCount} color="var(--vacant)" />
            <StatCell label="Occupied" value={occupiedCount} color="var(--occupied)" />
            <StatCell label="Load" value={`${occupancyPercent}%`} color={occupancyPercent > 70 ? "var(--warning)" : "var(--vacant)"} />
          </div>
          <div
            className="h-1.5 bg-[var(--bg-elevated)] flex"
            role="img"
            aria-label={`Slot distribution: ${vacantCount} vacant, ${occupiedCount} occupied out of ${mockSlots.length} total`}
          >
            <div className="h-full" style={{ width: `${(vacantCount / mockSlots.length) * 100}%`, backgroundColor: "var(--vacant)" }} />
            <div className="h-full" style={{ width: `${(occupiedCount / mockSlots.length) * 100}%`, backgroundColor: "var(--occupied)" }} />
          </div>
        </div>

        {/* Slot Grid */}
        <section className="mb-8" aria-label="Slot status grid">
          <SectionHeader title="Slot Status" />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" role="list">
            {mockSlots.map((slot, index) => (
              <div key={slot.id} role="listitem">
                <SlotCard slot={slot} index={index} />
              </div>
            ))}
          </div>
        </section>

        {/* Sensor Mapping */}
        <section className="border border-[var(--border-default)] bg-[var(--bg-secondary)]">
          <div className="px-4 py-3 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)]">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--text-muted)] font-display">
              Sensor Mapping
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-[var(--border-default)]">
            <SensorNode
              nodeId="ESP32-01"
              name="Node 1"
              slots="1-3"
              zone="A"
            />
            <SensorNode
              nodeId="ESP32-02"
              name="Node 2"
              slots="4-6"
              zone="B"
            />
          </div>
        </section>
      </main>
    </div>
  );
}

function SensorNode({
  nodeId,
  name,
  slots,
  zone,
}: {
  nodeId: string;
  name: string;
  slots: string;
  zone: string;
}) {
  return (
    <div className="flex items-center gap-4 p-4">
      <div className="flex h-10 w-20 items-center justify-center border border-[var(--accent)]/30 bg-[var(--bg-tertiary)] font-mono text-xs text-[var(--accent)]">
        {nodeId}
      </div>
      <div>
        <p className="font-semibold uppercase tracking-wide text-[var(--text-primary)] font-display">
          {name}
        </p>
        <p className="text-xs text-[var(--text-muted)]">
          Slots {slots} &bull; Zone {zone}
        </p>
      </div>
    </div>
  );
}
