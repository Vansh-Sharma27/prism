import type { ParkingLot, ParkingSlot, SystemStats } from "@/types/parking";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const OFFLINE_THRESHOLD_SECONDS = 30;

type SlotStatus = ParkingSlot["status"];

interface ApiLotsResponse {
  lots: ApiLot[];
  total: number;
}

interface ApiSlotsResponse {
  slots: ApiSlot[];
  total: number;
}

interface ApiEventsResponse {
  events: ApiEvent[];
  total: number;
}

interface ApiLot {
  id: string;
  name: string;
  location: string | null;
  total_slots: number;
  available_slots: number;
  latitude?: number | null;
  longitude?: number | null;
}

interface ApiSlot {
  id: string;
  lot_id: string;
  zone_id: string | null;
  zone_name?: string | null;
  slot_number: number;
  is_occupied: boolean;
  is_reserved: boolean;
  slot_type: string;
  sensor_id?: string | null;
  latest_distance_cm?: number | null;
  last_reading_at?: string | null;
  last_status_change?: string | null;
}

interface ApiEvent {
  id: number;
  event_type: "entry" | "exit";
  timestamp: string | null;
  slot_id: string;
  slot_number: number | null;
  lot_id: string | null;
  lot_name: string | null;
  sensor_distance_cm?: number | null;
}

export interface DashboardData {
  lots: ParkingLot[];
  slots: ParkingSlot[];
  stats: SystemStats;
}

export interface LotDetailData {
  lot: ParkingLot | null;
  slots: ParkingSlot[];
  zones: ZoneSummary[];
}

export interface ZoneSummary {
  id: string;
  name: string;
  total: number;
  occupied: number;
  vacant: number;
  offline: number;
}

export interface ActivityEvent {
  id: number;
  type: "entry" | "exit";
  timestamp: number;
  slot: string;
  lot: string;
}

function getBearerToken(): string | null {
  if (typeof window !== "undefined") {
    const clientToken = window.localStorage.getItem("prism_access_token");
    if (clientToken) {
      return clientToken;
    }
  }

  const envToken = process.env.NEXT_PUBLIC_API_TOKEN;
  return envToken || null;
}

async function fetchJson<T>(url: string): Promise<T> {
  const token = getBearerToken();
  const headers: HeadersInit = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  const res = await fetch(url, {
    cache: "no-store",
    headers,
  });

  if (res.status === 401) {
    throw new Error(
      "Unauthorized. Set prism_access_token in browser localStorage or NEXT_PUBLIC_API_TOKEN."
    );
  }

  if (!res.ok) {
    throw new Error(`Request failed (${res.status}) for ${url}`);
  }

  return res.json() as Promise<T>;
}

function parseTimestamp(value?: string | null): number {
  if (!value) {
    return Math.floor(Date.now() / 1000);
  }

  // Backend emits naive ISO strings (no timezone); interpret them as UTC.
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
  const normalized = hasTimezone ? value : `${value}Z`;

  const parsed = Date.parse(normalized);
  if (Number.isNaN(parsed)) {
    return Math.floor(Date.now() / 1000);
  }

  return Math.floor(parsed / 1000);
}

function formatSlotLabel(event: ApiEvent): string {
  if (typeof event.slot_number === "number") {
    return `S${event.slot_number.toString().padStart(2, "0")}`;
  }

  const match = event.slot_id.match(/slot-(\d+)$/);
  if (match) {
    return `S${match[1].padStart(2, "0")}`;
  }

  return event.slot_id.toUpperCase();
}

function deriveSensorId(slot: ApiSlot): string {
  if (slot.sensor_id && slot.sensor_id.trim().length > 0) {
    return slot.sensor_id;
  }

  const node = Math.ceil(slot.slot_number / 3);
  return `ESP32-${node.toString().padStart(2, "0")}`;
}

function deriveDistance(slot: ApiSlot): number {
  if (typeof slot.latest_distance_cm === "number") {
    return slot.latest_distance_cm;
  }

  return slot.is_occupied ? 10 : 120;
}

function deriveStatus(lastUpdate: number, occupied: boolean): SlotStatus {
  const ageSeconds = Math.floor(Date.now() / 1000) - lastUpdate;
  if (ageSeconds > OFFLINE_THRESHOLD_SECONDS) {
    return "offline";
  }

  return occupied ? "occupied" : "vacant";
}

function mapApiSlot(slot: ApiSlot): ParkingSlot {
  const lastUpdate = parseTimestamp(slot.last_reading_at || slot.last_status_change);
  const status = deriveStatus(lastUpdate, slot.is_occupied);

  return {
    id: slot.id,
    lotId: slot.lot_id,
    zoneId: slot.zone_id,
    zone: slot.zone_name || slot.zone_id || "Unassigned",
    slotNumber: slot.slot_number,
    sensorId: deriveSensorId(slot),
    status,
    distanceCm: deriveDistance(slot),
    lastUpdate,
  };
}

function mapLotFromSlots(apiLot: ApiLot, slotsForLot: ParkingSlot[]): ParkingLot {
  const occupiedSlots = slotsForLot.filter((slot) => slot.status === "occupied").length;
  const offlineSlots = slotsForLot.filter((slot) => slot.status === "offline").length;
  const lotLastSync = slotsForLot.length > 0
    ? Math.max(...slotsForLot.map((slot) => slot.lastUpdate))
    : Math.floor(Date.now() / 1000);

  return {
    id: apiLot.id,
    name: apiLot.name,
    location: apiLot.location || "Unknown",
    totalSlots: apiLot.total_slots,
    occupiedSlots,
    offlineSlots,
    slots: slotsForLot,
    lastSync: lotLastSync,
  };
}

function buildSystemStats(lots: ParkingLot[], slots: ParkingSlot[]): SystemStats {
  const totalLots = lots.length;
  const totalSlots = lots.reduce((sum, lot) => sum + lot.totalSlots, 0);
  const occupiedSlots = slots.filter((slot) => slot.status === "occupied").length;
  const offlineSlots = slots.filter((slot) => slot.status === "offline").length;
  const vacantSlots = Math.max(totalSlots - occupiedSlots - offlineSlots, 0);
  const occupancyRate = totalSlots > 0 ? Math.round((occupiedSlots / totalSlots) * 100) : 0;

  const lastUpdate = slots.length > 0
    ? Math.max(...slots.map((slot) => slot.lastUpdate))
    : Math.floor(Date.now() / 1000);

  return {
    totalLots,
    totalSlots,
    occupiedSlots,
    vacantSlots,
    offlineSlots,
    occupancyRate,
    lastUpdate,
  };
}

function buildZoneSummary(slots: ParkingSlot[]): ZoneSummary[] {
  const zoneMap = new Map<string, ZoneSummary>();

  for (const slot of slots) {
    const zoneId = slot.zoneId || "unassigned";
    const zoneName = slot.zone || "Unassigned";
    const current = zoneMap.get(zoneId) || {
      id: zoneId,
      name: zoneName,
      total: 0,
      occupied: 0,
      vacant: 0,
      offline: 0,
    };

    current.total += 1;
    if (slot.status === "occupied") {
      current.occupied += 1;
    } else if (slot.status === "vacant") {
      current.vacant += 1;
    } else {
      current.offline += 1;
    }

    zoneMap.set(zoneId, current);
  }

  return Array.from(zoneMap.values()).sort((a, b) => a.name.localeCompare(b.name));
}

export async function fetchLots(): Promise<ParkingLot[]> {
  const [lotsResponse, slotsResponse] = await Promise.all([
    fetchJson<ApiLotsResponse>(`${API_BASE}/lots`),
    fetchJson<ApiSlotsResponse>(`${API_BASE}/slots`),
  ]);

  const mappedSlots = slotsResponse.slots.map(mapApiSlot);
  return lotsResponse.lots.map((lot) => {
    const slotsForLot = mappedSlots.filter((slot) => slot.lotId === lot.id);
    return mapLotFromSlots(lot, slotsForLot);
  });
}

export async function fetchDashboardData(): Promise<DashboardData> {
  const [lotsResponse, slotsResponse] = await Promise.all([
    fetchJson<ApiLotsResponse>(`${API_BASE}/lots`),
    fetchJson<ApiSlotsResponse>(`${API_BASE}/slots`),
  ]);

  const mappedSlots = slotsResponse.slots.map(mapApiSlot);
  const lots = lotsResponse.lots.map((lot) => {
    const slotsForLot = mappedSlots.filter((slot) => slot.lotId === lot.id);
    return mapLotFromSlots(lot, slotsForLot);
  });

  const stats = buildSystemStats(lots, mappedSlots);

  return {
    lots,
    slots: mappedSlots,
    stats,
  };
}

export async function fetchLotDetailData(lotId: string): Promise<LotDetailData> {
  const [lotResponse, slotsResponse] = await Promise.all([
    fetchJson<ApiLot>(`${API_BASE}/lots/${lotId}`),
    fetchJson<ApiSlotsResponse>(`${API_BASE}/slots?lot_id=${lotId}`),
  ]);

  const mappedSlots = slotsResponse.slots.map(mapApiSlot);
  const lot = mapLotFromSlots(lotResponse, mappedSlots);

  return {
    lot,
    slots: mappedSlots,
    zones: buildZoneSummary(mappedSlots),
  };
}

export async function fetchActivityEvents(limit = 120): Promise<ActivityEvent[]> {
  const response = await fetchJson<ApiEventsResponse>(`${API_BASE}/events?limit=${limit}`);

  return response.events.map((event) => ({
    id: event.id,
    type: event.event_type,
    timestamp: parseTimestamp(event.timestamp) * 1000,
    slot: formatSlotLabel(event),
    lot: event.lot_name || event.lot_id || "Unknown",
  }));
}
