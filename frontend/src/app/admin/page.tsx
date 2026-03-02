import type { Metadata } from "next";
import { AdminClient } from "@/app/admin/admin-client";

export const metadata: Metadata = {
  title: "Admin | PRISM",
};

export default function AdminPage() {
  return <AdminClient />;
}
