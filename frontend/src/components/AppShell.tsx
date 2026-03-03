import { Navbar } from "@/components/Navbar";
import type { ReactNode } from "react";

const DEFAULT_MAIN_CLASS =
  "mx-auto max-w-7xl px-4 pb-16 pt-24 sm:px-6";

interface AppShellProps {
  children: ReactNode;
  mainClassName?: string;
}

export function AppShell({
  children,
  mainClassName = DEFAULT_MAIN_CLASS,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <Navbar />
      <main id="main-content" className={mainClassName}>
        {children}
      </main>
    </div>
  );
}
