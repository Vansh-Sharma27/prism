import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Configuration | PRISM",
};

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
