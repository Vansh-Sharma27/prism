import { LotsClient } from "@/app/lots/lots-client";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Parking Lots | PRISM",
};

export default function LotsPage() {
  return <LotsClient />;
}
