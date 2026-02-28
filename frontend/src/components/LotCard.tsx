import Link from "next/link";
import type { ParkingLot } from "@/types/parking";
import { formatTimestamp } from "@/lib/format";
import { MapPin, ChevronRight, Wifi, WifiOff, AlertTriangle } from "lucide-react";

interface LotCardProps {
  lot: ParkingLot;
  index: number;
}

export function LotCard({ lot, index }: LotCardProps) {
  const vacantSlots = lot.totalSlots - lot.occupiedSlots - lot.offlineSlots;
  const occupiedPercent = (lot.occupiedSlots / lot.totalSlots) * 100;
  const vacantPercent = (vacantSlots / lot.totalSlots) * 100;
  const offlinePercent = (lot.offlineSlots / lot.totalSlots) * 100;

  const isHealthy = lot.offlineSlots === 0;
  const isCritical = occupiedPercent >= 90;
  const isHighLoad = occupiedPercent >= 70;

  const statusColor = isCritical
    ? "var(--occupied)"
    : isHighLoad
      ? "var(--warning)"
      : "var(--vacant)";

  const statusLabel = isCritical ? "Critical" : isHighLoad ? "High Load" : "Normal";

  return (
    <Link
      href={`/lots/${lot.id}`}
      className="group block border border-[var(--border-default)] bg-[var(--bg-secondary)]
        transition-all duration-200 ease-out
        hover:border-[var(--accent)] hover:translate-y-[-3px] hover:shadow-xl hover:shadow-black/30
        focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-primary)]
        animate-scale-in"
      style={{ animationDelay: `${index * 75}ms` }}
      aria-label={`${lot.name}: ${vacantSlots} vacant, ${lot.occupiedSlots} occupied. Status: ${statusLabel}`}
    >
      {/* Top accent bar - animated on hover */}
      <div
        className="h-1 transition-all duration-200 group-hover:h-1.5"
        style={{ backgroundColor: statusColor }}
      />

      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-[var(--border-subtle)]">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold uppercase tracking-wide text-[var(--text-primary)] font-display group-hover:text-[var(--accent)] transition-colors truncate">
            {lot.name}
          </h3>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
            <MapPin size={12} className="shrink-0" />
            <span className="truncate">{lot.location || "—"}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 ml-2 shrink-0">
          {!isHealthy && (
            <AlertTriangle size={14} className="text-[var(--warning)] animate-pulse-warning" />
          )}
          {isHealthy ? (
            <Wifi size={14} className="text-[var(--vacant)]" />
          ) : (
            <WifiOff size={14} className="text-[var(--offline)]" />
          )}
          <ChevronRight
            size={18}
            className="text-[var(--text-muted)] transition-all duration-200 group-hover:translate-x-1 group-hover:text-[var(--accent)]"
          />
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 divide-x divide-[var(--border-subtle)]">
        <LotStatCell label="Vacant" value={vacantSlots} color="var(--vacant)" />
        <LotStatCell label="Occupied" value={lot.occupiedSlots} color="var(--occupied)" />
        <LotStatCell
          label={lot.offlineSlots > 0 ? "Offline" : "Total"}
          value={lot.offlineSlots > 0 ? lot.offlineSlots : lot.totalSlots}
          color={lot.offlineSlots > 0 ? "var(--offline)" : "var(--text-secondary)"}
        />
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-[var(--bg-elevated)] flex overflow-hidden">
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${vacantPercent}%`, backgroundColor: "var(--vacant)" }}
        />
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${occupiedPercent}%`, backgroundColor: "var(--occupied)" }}
        />
        {lot.offlineSlots > 0 && (
          <div
            className="h-full transition-all duration-500"
            style={{ width: `${offlinePercent}%`, backgroundColor: "var(--offline)" }}
          />
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[var(--bg-tertiary)]">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-sm"
            style={{ backgroundColor: statusColor }}
          />
          <span
            className="text-xs font-semibold uppercase tracking-wider font-display"
            style={{ color: statusColor }}
          >
            {statusLabel}
          </span>
        </div>
        <span className="font-mono text-[10px] text-[var(--text-muted)] tabular-nums">
          {formatTimestamp(lot.lastSync)}
        </span>
      </div>
    </Link>
  );
}

function LotStatCell({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="px-4 py-3 text-center group-hover:bg-[var(--bg-tertiary)]/50 transition-colors">
      <div className="font-mono text-2xl font-bold tabular-nums transition-transform group-hover:scale-105" style={{ color }}>
        {value.toString().padStart(2, "0")}
      </div>
      <div className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display">
        {label}
      </div>
    </div>
  );
}
