import { ActivityClient } from "@/app/activity/activity-client";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Activity Log | PRISM",
};

export default function ActivityPage() {
  return <ActivityClient />;
}
