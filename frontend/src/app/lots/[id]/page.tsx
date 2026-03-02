import { LotDetailClient } from "@/app/lots/[id]/lot-detail-client";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Lot Details | PRISM",
};

interface LotDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function LotDetailPage({ params }: LotDetailPageProps) {
  const { id } = await params;

  return <LotDetailClient lotId={id} />;
}
