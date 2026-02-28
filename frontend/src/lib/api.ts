const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api";

export async function fetchLots() {
  const res = await fetch(`${API_BASE}/lots`, {
    next: { revalidate: 10 },
  });
  if (!res.ok) throw new Error("Failed to fetch lots");
  return res.json();
}

export async function fetchLot(id: string) {
  const res = await fetch(`${API_BASE}/lots/${id}`, {
    next: { revalidate: 5 },
  });
  if (!res.ok) throw new Error("Failed to fetch lot");
  return res.json();
}

export async function fetchSlots(lotId: string) {
  const res = await fetch(`${API_BASE}/lots/${lotId}/slots`, {
    next: { revalidate: 5 },
  });
  if (!res.ok) throw new Error("Failed to fetch slots");
  return res.json();
}
