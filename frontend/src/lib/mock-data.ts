import type { ParkingLot, ParkingSlot, SystemStats } from "@/types/parking";

export const mockLots: ParkingLot[] = [
  {
    id: "lot-a",
    name: "Main Building",
    location: "Block A, Ground Floor",
    totalSlots: 6,
    occupiedSlots: 4,
    offlineSlots: 0,
    slots: [],
    lastSync: Math.floor(Date.now() / 1000) - 15,
  },
  {
    id: "lot-b",
    name: "East Wing",
    location: "Block B, Level 1",
    totalSlots: 8,
    occupiedSlots: 3,
    offlineSlots: 1,
    slots: [],
    lastSync: Math.floor(Date.now() / 1000) - 45,
  },
  {
    id: "lot-c",
    name: "Visitor Parking",
    location: "Entrance Gate",
    totalSlots: 4,
    occupiedSlots: 2,
    offlineSlots: 0,
    slots: [],
    lastSync: Math.floor(Date.now() / 1000) - 8,
  },
];

export const mockSlots: ParkingSlot[] = [
  { id: "lot-a-slot-1", sensorId: "ESP32-01", status: "occupied", distanceCm: 8.4, lastUpdate: Math.floor(Date.now() / 1000) - 5, zone: "A" },
  { id: "lot-a-slot-2", sensorId: "ESP32-01", status: "vacant", distanceCm: 124.2, lastUpdate: Math.floor(Date.now() / 1000) - 12, zone: "A" },
  { id: "lot-a-slot-3", sensorId: "ESP32-01", status: "occupied", distanceCm: 6.1, lastUpdate: Math.floor(Date.now() / 1000) - 3, zone: "A" },
  { id: "lot-a-slot-4", sensorId: "ESP32-02", status: "vacant", distanceCm: 89.7, lastUpdate: Math.floor(Date.now() / 1000) - 8, zone: "B" },
  { id: "lot-a-slot-5", sensorId: "ESP32-02", status: "occupied", distanceCm: 11.3, lastUpdate: Math.floor(Date.now() / 1000) - 2, zone: "B" },
  { id: "lot-a-slot-6", sensorId: "ESP32-02", status: "occupied", distanceCm: 7.8, lastUpdate: Math.floor(Date.now() / 1000) - 18, zone: "B" },
];

export const mockStats: SystemStats = {
  totalLots: 3,
  totalSlots: 18,
  occupiedSlots: 9,
  vacantSlots: 8,
  offlineSlots: 1,
  occupancyRate: 50,
  lastUpdate: Math.floor(Date.now() / 1000),
};

export const mockEvents = [
  { id: 1, slot: "A1", lot: "Main Building", type: "entry" as const, timestamp: Date.now() - 120000 },
  { id: 2, slot: "B3", lot: "East Wing", type: "exit" as const, timestamp: Date.now() - 300000 },
  { id: 3, slot: "A4", lot: "Main Building", type: "entry" as const, timestamp: Date.now() - 480000 },
  { id: 4, slot: "C2", lot: "Visitor Parking", type: "exit" as const, timestamp: Date.now() - 720000 },
  { id: 5, slot: "A2", lot: "Main Building", type: "entry" as const, timestamp: Date.now() - 900000 },
  { id: 6, slot: "B1", lot: "East Wing", type: "exit" as const, timestamp: Date.now() - 1080000 },
  { id: 7, slot: "A6", lot: "Main Building", type: "entry" as const, timestamp: Date.now() - 1320000 },
  { id: 8, slot: "C1", lot: "Visitor Parking", type: "entry" as const, timestamp: Date.now() - 1500000 },
];
