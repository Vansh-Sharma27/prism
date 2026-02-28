import type { ParkingSlot } from "@/types/parking";
import { formatTimestamp } from "@/lib/format";
import { Car, Circle } from "lucide-react";

interface SlotCardProps {
  slot: ParkingSlot;
  index: number;
}

export function SlotCard({ slot, index }: SlotCardProps) {
  const statusConfig = {
    vacant: {
      bg: "bg-[var(--vacant)]/5",
      border: "border-[var(--vacant)]/30",
      hoverBorder: "hover:border-[var(--vacant)]",
      text: "text-[var(--vacant)]",
      label: "VACANT",
      dotClass: "status-dot-vacant",
      barColor: "var(--vacant)",
    },
    occupied: {
      bg: "bg-[var(--occupied)]/5",
      border: "border-[var(--occupied)]/30",
      hoverBorder: "hover:border-[var(--occupied)]",
      text: "text-[var(--occupied)]",
      label: "OCCUPIED",
      dotClass: "status-dot-occupied",
      barColor: "var(--occupied)",
    },
    offline: {
      bg: "bg-[var(--offline)]/10",
      border: "border-[var(--offline)]/30",
      hoverBorder: "hover:border-[var(--offline)]",
      text: "text-[var(--offline)]",
      label: "OFFLINE",
      dotClass: "status-dot-offline",
      barColor: "var(--offline)",
    },
  };

  const config = statusConfig[slot.status];
  const timeSinceUpdate = Math.floor((Date.now() - slot.lastUpdate * 1000) / 1000);
  const isStale = timeSinceUpdate > 60;
  const slotNumber = slot.id.split("-").pop()?.toUpperCase() || "—";

  return (
    <div
      role="group"
      className={`
        w-full text-left
        border ${config.border} ${config.bg}
        transition-all duration-200 ease-out
        ${config.hoverBorder}
        hover:translate-y-[-2px] hover:shadow-lg
        animate-scale-in
        group
      `}
      style={{ animationDelay: `${index * 50}ms` }}
      aria-label={`Slot ${slotNumber}: ${config.label}, distance ${slot.distanceCm.toFixed(1)} centimeters`}
    >
      {/* Top indicator bar */}
      <div
        className="h-1 transition-all group-hover:h-1.5"
        style={{ backgroundColor: config.barColor }}
      />

      {/* Main content */}
      <div className="p-3">
        <div className="flex items-start justify-between">
          <div>
            <span className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
              {slot.sensorId}
            </span>
            <div className={`font-mono text-2xl font-bold ${config.text} transition-transform group-hover:scale-105`}>
              {slotNumber}
            </div>
          </div>

          <div
            className={`flex h-8 w-8 items-center justify-center border ${config.border} ${config.bg} transition-all group-hover:scale-110`}
          >
            {slot.status === "occupied" ? (
              <Car className={config.text} size={16} />
            ) : (
              <Circle className={config.text} size={16} strokeWidth={1.5} />
            )}
          </div>
        </div>

        {/* Distance reading */}
        <div className="mt-3 flex items-baseline gap-1">
          <span className="font-mono text-lg font-semibold text-[var(--text-primary)] tabular-nums">
            {slot.distanceCm.toFixed(1)}
          </span>
          <span className="font-mono text-xs text-[var(--text-muted)]">cm</span>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-3 py-2 bg-[var(--bg-tertiary)]">
        <div className="flex items-center gap-2">
          <span className={`status-dot ${config.dotClass} ${slot.status === "occupied" ? "animate-pulse-indicator" : ""}`} />
          <span
            className={`text-[10px] font-semibold uppercase tracking-wider font-display ${config.text}`}
          >
            {config.label}
          </span>
        </div>
        <span
          className={`font-mono text-[10px] tabular-nums ${
            isStale ? "text-[var(--warning)] animate-pulse-warning" : "text-[var(--text-muted)]"
          }`}
          title={isStale ? "Stale data - update delayed" : "Last update time"}
        >
          {formatTimestamp(slot.lastUpdate)}
        </span>
      </div>
    </div>
  );
}
