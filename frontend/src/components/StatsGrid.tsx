import type { SystemStats } from "@/types/parking";

interface StatsGridProps {
  stats: SystemStats;
}

export function StatsGrid({ stats }: StatsGridProps) {
  const items = [
    {
      label: "Total",
      value: stats.totalSlots,
      color: "var(--accent)",
    },
    {
      label: "Vacant",
      value: stats.vacantSlots,
      color: "var(--vacant)",
    },
    {
      label: "Occupied",
      value: stats.occupiedSlots,
      color: "var(--occupied)",
    },
    {
      label: "Offline",
      value: stats.offlineSlots,
      color: "var(--offline)",
    },
  ];

  const occupancyColor =
    stats.occupancyRate > 85
      ? "var(--occupied)"
      : stats.occupancyRate > 60
        ? "var(--warning)"
        : "var(--vacant)";

  const vacantPercent = (stats.vacantSlots / stats.totalSlots) * 100;
  const occupiedPercent = (stats.occupiedSlots / stats.totalSlots) * 100;
  const offlinePercent = (stats.offlineSlots / stats.totalSlots) * 100;

  return (
    <div className="border border-[var(--border-default)] bg-[var(--bg-secondary)]">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)]">
        <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display">
          System Status
        </span>
        <span className="font-mono text-xs text-[var(--accent)]">
          SLOTS
        </span>
      </div>

      {/* Stats row - responsive: 2-col on mobile, 5-col on md+ */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-[var(--border-default)]">
        {items.map((item) => (
          <div key={item.label} className="px-4 py-3 md:py-4 text-center">
            <div
              className="font-mono text-2xl md:text-3xl font-bold tabular-nums"
              style={{ color: item.color }}
              aria-label={`${item.label}: ${item.value}`}
            >
              {item.value.toString().padStart(2, "0")}
            </div>
            <div className="mt-1 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display">
              {item.label}
            </div>
          </div>
        ))}

        {/* Occupancy percentage */}
        <div className="col-span-2 sm:col-span-1 px-4 py-3 md:py-4 text-center bg-[var(--bg-tertiary)]">
          <div className="flex items-baseline justify-center gap-1">
            <span
              className="font-mono text-2xl md:text-3xl font-bold tabular-nums"
              style={{ color: occupancyColor }}
              aria-label={`Occupancy rate: ${stats.occupancyRate} percent`}
            >
              {stats.occupancyRate}
            </span>
            <span
              className="font-mono text-lg"
              style={{ color: occupancyColor }}
              aria-hidden="true"
            >
              %
            </span>
          </div>
          <div className="mt-1 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display">
            Load
          </div>
        </div>
      </div>

      {/* Progress bar - accessible */}
      <div
        className="h-2 bg-[var(--bg-elevated)] flex"
        role="img"
        aria-label={`Slot distribution: ${stats.vacantSlots} vacant, ${stats.occupiedSlots} occupied, ${stats.offlineSlots} offline out of ${stats.totalSlots} total`}
      >
        <div
          className="h-full transition-all duration-500"
          style={{
            width: `${vacantPercent}%`,
            backgroundColor: "var(--vacant)",
          }}
          aria-hidden="true"
        />
        <div
          className="h-full transition-all duration-500"
          style={{
            width: `${occupiedPercent}%`,
            backgroundColor: "var(--occupied)",
          }}
          aria-hidden="true"
        />
        <div
          className="h-full transition-all duration-500"
          style={{
            width: `${offlinePercent}%`,
            backgroundColor: "var(--offline)",
          }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
