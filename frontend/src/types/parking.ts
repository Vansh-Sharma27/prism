export interface ParkingSlot {
  id: string;
  sensorId: string;
  status: "vacant" | "occupied" | "offline";
  distanceCm: number;
  lastUpdate: number;
  zone?: string;
}

export interface ParkingLot {
  id: string;
  name: string;
  location: string;
  totalSlots: number;
  occupiedSlots: number;
  offlineSlots: number;
  slots: ParkingSlot[];
  lastSync: number;
}

export interface SystemStats {
  totalLots: number;
  totalSlots: number;
  occupiedSlots: number;
  vacantSlots: number;
  offlineSlots: number;
  occupancyRate: number;
  lastUpdate: number;
}
