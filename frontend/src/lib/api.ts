import type { ParkingLot, ParkingSlot, SystemStats } from "@/types/parking";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const OFFLINE_THRESHOLD_SECONDS = 30;
export const AUTH_TOKEN_STORAGE_KEY = "prism_access_token";
export const AUTH_SESSION_INVALID_EVENT = "prism:auth-session-invalid";

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

interface ApiAdminSensorsResponse {
  sensors: ApiAdminSensor[];
  summary: ApiAdminSensorsSummary;
}

interface ApiAdminAnalyticsResponse {
  window_days: number;
  daily_occupancy_average: ApiDailyOccupancyAverage[];
  peak_hour: ApiPeakHour;
  hourly_event_distribution: ApiHourlyDistributionRow[];
  zone_utilization_comparison: ApiZoneUtilizationRow[];
  generated_at: string;
}

interface ApiAuthResponse {
  access_token: string;
  user: AuthUser;
}

interface ApiRegisterResponse {
  message: string;
  user: AuthUser;
}

interface ApiCurrentUserResponse {
  user: AuthUser;
}

interface ApiErrorResponse {
  error?: string;
  details?: unknown;
}

interface FetchJsonOptions {
  includeAuth?: boolean;
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

interface ApiAdminSensorSlot {
  slot_id: string;
  lot_id: string;
  zone_id: string | null;
  slot_number: number;
  is_occupied: boolean;
  last_seen_at: string | null;
  last_distance_cm: number | null;
  telemetry_status: "online" | "offline";
}

interface ApiAdminSensor {
  sensor_id: string;
  total_slots: number;
  occupied_slots: number;
  offline_slots: number;
  last_seen_at: string | null;
  last_distance_cm: number | null;
  status: "online" | "degraded" | "offline";
  uptime_24h_pct?: number;
  slots: ApiAdminSensorSlot[];
}

interface ApiAdminSensorsSummary {
  total_sensors: number;
  online_sensors: number;
  degraded_sensors: number;
  offline_sensors: number;
  offline_threshold_seconds: number;
}

interface ApiDailyOccupancyAverage {
  date: string;
  avg_occupancy_pct: number;
  samples: number;
}

interface ApiPeakHour {
  hour_utc: string | null;
  events: number;
}

interface ApiHourlyDistributionRow {
  hour: number;
  events: number;
}

interface ApiZoneUtilizationRow {
  zone_id: string;
  zone_name: string;
  lot_id: string;
  lot_name: string | null;
  occupied_slots: number;
  total_slots: number;
  utilization_pct: number;
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

export interface AdminSensorSlot {
  slotId: string;
  lotId: string;
  zoneId: string | null;
  slotNumber: number;
  isOccupied: boolean;
  lastSeenAt: string | null;
  lastDistanceCm: number | null;
  telemetryStatus: "online" | "offline";
}

export interface AdminSensorRow {
  sensorId: string;
  totalSlots: number;
  occupiedSlots: number;
  offlineSlots: number;
  lastSeenAt: string | null;
  lastDistanceCm: number | null;
  status: "online" | "degraded" | "offline";
  uptime24hPct: number;
  slots: AdminSensorSlot[];
}

export interface AdminSensorsSummary {
  totalSensors: number;
  onlineSensors: number;
  degradedSensors: number;
  offlineSensors: number;
  offlineThresholdSeconds: number;
}

export interface AdminSensorsData {
  sensors: AdminSensorRow[];
  summary: AdminSensorsSummary;
}

export interface AdminDailyOccupancyRow {
  date: string;
  avgOccupancyPct: number;
  samples: number;
}

export interface AdminHourlyDistributionRow {
  hour: number;
  events: number;
}

export interface AdminZoneUtilizationRow {
  zoneId: string;
  zoneName: string;
  lotId: string;
  lotName: string | null;
  occupiedSlots: number;
  totalSlots: number;
  utilizationPct: number;
}

export interface AdminAnalyticsData {
  windowDays: number;
  dailyOccupancyAverage: AdminDailyOccupancyRow[];
  peakHour: {
    hourUtc: string | null;
    events: number;
  };
  hourlyEventDistribution: AdminHourlyDistributionRow[];
  zoneUtilizationComparison: AdminZoneUtilizationRow[];
  generatedAt: string;
}

export interface AuthUser {
  id: number;
  email: string;
  role: "student" | "faculty" | "admin";
  created_at?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
}

async function parseApiErrorMessage(res: Response): Promise<string> {
  let defaultMessage = `Request failed (${res.status})`;
  if (res.status === 401) {
    defaultMessage = "Authentication required.";
  } else if (res.status === 403) {
    defaultMessage = "Permission denied.";
  }

  try {
    const payload = (await res.json()) as ApiErrorResponse;
    if (typeof payload.error === "string" && payload.error.trim().length > 0) {
      return payload.error;
    }

    if (payload.details && typeof payload.details === "object") {
      const flat = JSON.stringify(payload.details);
      if (flat.length > 0) {
        return `${defaultMessage} ${flat}`;
      }
    }
  } catch {
    // Ignore parse failures and return generic message.
  }

  return defaultMessage;
}

function getBearerToken(): string | null {
  if (typeof window !== "undefined") {
    let clientToken: string | null = null;
    try {
      clientToken = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    } catch {
      clientToken = null;
    }
    if (clientToken) {
      return clientToken;
    }
  }

  const envToken = process.env.NEXT_PUBLIC_API_TOKEN;
  return envToken || null;
}

function notifySessionInvalid(status: number, url: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent(AUTH_SESSION_INVALID_EVENT, {
      detail: { status, url },
    })
  );
}

async function fetchJson<T>(url: string, init?: RequestInit, options?: FetchJsonOptions): Promise<T> {
  const includeAuth = options?.includeAuth ?? true;
  const token = includeAuth ? getBearerToken() : null;
  const baseHeaders: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
  const headers: HeadersInit = {
    ...baseHeaders,
    ...(init?.headers || {}),
  };
  const res = await fetch(url, {
    cache: "no-store",
    ...init,
    headers,
  });

  if ((res.status === 401 || res.status === 422) && includeAuth) {
    notifySessionInvalid(res.status, url);
    throw new Error("Unauthorized. Please login again.");
  }

  if (!res.ok) {
    const message = await parseApiErrorMessage(res);
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

export async function loginUser(payload: LoginPayload): Promise<{
  accessToken: string;
  user: AuthUser;
}> {
  const response = await fetchJson<ApiAuthResponse>(
    `${API_BASE}/auth/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    { includeAuth: false }
  );

  return {
    accessToken: response.access_token,
    user: response.user,
  };
}

export async function registerUser(payload: RegisterPayload): Promise<AuthUser> {
  const response = await fetchJson<ApiRegisterResponse>(
    `${API_BASE}/auth/register`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    { includeAuth: false }
  );

  return response.user;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const response = await fetchJson<ApiCurrentUserResponse>(`${API_BASE}/auth/me`);
  return response.user;
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

function mapAdminSensorSlot(slot: ApiAdminSensorSlot): AdminSensorSlot {
  return {
    slotId: slot.slot_id,
    lotId: slot.lot_id,
    zoneId: slot.zone_id,
    slotNumber: slot.slot_number,
    isOccupied: slot.is_occupied,
    lastSeenAt: slot.last_seen_at,
    lastDistanceCm: slot.last_distance_cm,
    telemetryStatus: slot.telemetry_status,
  };
}

function mapAdminSensor(sensor: ApiAdminSensor): AdminSensorRow {
  return {
    sensorId: sensor.sensor_id,
    totalSlots: sensor.total_slots,
    occupiedSlots: sensor.occupied_slots,
    offlineSlots: sensor.offline_slots,
    lastSeenAt: sensor.last_seen_at,
    lastDistanceCm: sensor.last_distance_cm,
    status: sensor.status,
    uptime24hPct: typeof sensor.uptime_24h_pct === "number" ? sensor.uptime_24h_pct : 0,
    slots: sensor.slots.map(mapAdminSensorSlot),
  };
}

export async function fetchAdminSensors(offlineAfterSeconds = 90): Promise<AdminSensorsData> {
  const safeThreshold = Math.max(30, Math.min(offlineAfterSeconds, 600));
  const response = await fetchJson<ApiAdminSensorsResponse>(
    `${API_BASE}/admin/sensors?offline_after_seconds=${safeThreshold}`
  );

  return {
    sensors: response.sensors.map(mapAdminSensor),
    summary: {
      totalSensors: response.summary.total_sensors,
      onlineSensors: response.summary.online_sensors,
      degradedSensors: response.summary.degraded_sensors,
      offlineSensors: response.summary.offline_sensors,
      offlineThresholdSeconds: response.summary.offline_threshold_seconds,
    },
  };
}

export async function fetchAdminAnalytics(days = 7): Promise<AdminAnalyticsData> {
  const safeDays = Math.max(1, Math.min(days, 30));
  const response = await fetchJson<ApiAdminAnalyticsResponse>(
    `${API_BASE}/admin/analytics?days=${safeDays}`
  );

  return {
    windowDays: response.window_days,
    dailyOccupancyAverage: response.daily_occupancy_average.map((row) => ({
      date: row.date,
      avgOccupancyPct: row.avg_occupancy_pct,
      samples: row.samples,
    })),
    peakHour: {
      hourUtc: response.peak_hour.hour_utc,
      events: response.peak_hour.events,
    },
    hourlyEventDistribution: response.hourly_event_distribution.map((row) => ({
      hour: row.hour,
      events: row.events,
    })),
    zoneUtilizationComparison: response.zone_utilization_comparison.map((row) => ({
      zoneId: row.zone_id,
      zoneName: row.zone_name,
      lotId: row.lot_id,
      lotName: row.lot_name,
      occupiedSlots: row.occupied_slots,
      totalSlots: row.total_slots,
      utilizationPct: row.utilization_pct,
    })),
    generatedAt: response.generated_at,
  };
}
