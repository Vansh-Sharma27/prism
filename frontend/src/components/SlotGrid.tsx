import type { ParkingSlot } from "@/types/parking";

interface SlotGridProps {
  slots: ParkingSlot[];
}

export function SlotGrid({ slots }: SlotGridProps) {
  const getStatusClasses = (status: ParkingSlot["status"]) => {
    switch (status) {
      case "vacant":
        return "border-[var(--vacant)]/50 bg-[var(--vacant)]/10 text-[var(--vacant)]";
      case "occupied":
        return "border-[var(--occupied)]/50 bg-[var(--occupied)]/10 text-[var(--occupied)]";
      case "offline":
        return "border-[var(--offline)]/50 bg-[var(--offline)]/10 text-[var(--offline)]";
      default:
        return "border-[var(--border-default)] bg-[var(--bg-tertiary)] text-[var(--text-muted)]";
    }
  };

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6" role="list" aria-label="Slot status blocks">
      {slots.map((slot) => (
        <div
          key={slot.id}
          role="listitem"
          className={`border p-3 text-center transition-colors ${getStatusClasses(slot.status)}`}
        >
          <div className="font-mono text-xs uppercase tracking-wider text-[var(--text-muted)]">
            {slot.sensorId}
          </div>
          <div className="mt-1 font-mono text-lg font-bold">S{slot.slotNumber.toString().padStart(2, "0")}</div>
          <div className="mt-1 text-[10px] font-semibold uppercase tracking-wider">{slot.status}</div>
        </div>
      ))}
    </div>
  );
}
