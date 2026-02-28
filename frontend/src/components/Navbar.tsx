"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Car,
  Activity,
  Settings,
  Menu,
  X,
  Radio,
} from "lucide-react";
import { useState, useEffect } from "react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/lots", label: "Lots", icon: Car },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Config", icon: Settings },
];

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function Navbar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    setTime(formatTime(new Date()));
    const interval = setInterval(() => {
      setTime(formatTime(new Date()));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="fixed top-0 left-0 right-0 z-50">
      <nav className="bg-[var(--bg-secondary)]/95 backdrop-blur-sm border-b border-[var(--border-default)]" aria-label="Main navigation">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="flex h-14 items-center justify-between">
            {/* Logo */}
            <Link
              href="/"
              className="flex items-center gap-3 group focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-secondary)]"
            >
              {/* Industrial prism icon */}
              <div className="relative flex h-9 w-9 items-center justify-center border border-[var(--accent)]/60 bg-[var(--bg-elevated)] transition-all group-hover:border-[var(--accent)] group-hover:shadow-[0_0_12px_rgba(245,158,11,0.3)]">
                <svg viewBox="0 0 32 32" className="h-6 w-6 transition-transform group-hover:scale-110">
                  <polygon
                    points="16,4 28,26 4,26"
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="2"
                    strokeLinejoin="bevel"
                  />
                  <line
                    x1="16"
                    y1="4"
                    x2="12"
                    y2="20"
                    stroke="var(--accent)"
                    strokeWidth="1.5"
                    opacity="0.6"
                  />
                  <line
                    x1="12"
                    y1="20"
                    x2="20"
                    y2="20"
                    stroke="var(--accent)"
                    strokeWidth="1.5"
                    opacity="0.4"
                  />
                </svg>
              </div>

              <div className="hidden sm:block">
                <span className="text-xl font-bold tracking-wider text-[var(--text-primary)] font-display group-hover:text-[var(--accent)] transition-colors">
                  PRISM
                </span>
                <span className="ml-2 text-xs text-[var(--text-muted)] font-mono tracking-widest">
                  v1.0
                </span>
              </div>
            </Link>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center gap-1">
              {navItems.map(({ href, label, icon: Icon }) => {
                const isActive = pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold uppercase tracking-wider transition-all font-display focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-secondary)] ${
                      isActive
                        ? "bg-[var(--accent)] text-[var(--bg-primary)]"
                        : "text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] hover:text-[var(--accent)]"
                    }`}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <Icon size={16} strokeWidth={2} aria-hidden="true" />
                    {label}
                  </Link>
                );
              })}
            </div>

            {/* Status Bar */}
            <div className="hidden md:flex items-center gap-6">
              {/* System time */}
              <div className="flex items-center gap-2 font-mono text-sm">
                <span className="text-[var(--text-muted)]">SYS</span>
                <span className="text-[var(--accent)] tabular-nums font-semibold">{time}</span>
              </div>

              {/* Connection status - live pulsing indicator */}
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--vacant)] opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--vacant)]"></span>
                </span>
                <span className="font-mono text-xs text-[var(--vacant)] uppercase tracking-wider font-semibold">
                  Live
                </span>
              </div>
            </div>

            {/* Mobile Menu Button - minimum 44x44 touch target */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="flex md:hidden h-11 w-11 items-center justify-center bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)] cursor-pointer focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-secondary)]"
              aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={mobileOpen}
              aria-controls="mobile-nav"
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile Nav */}
        {mobileOpen && (
          <div id="mobile-nav" className="md:hidden border-t border-[var(--border-default)] bg-[var(--bg-tertiary)] animate-fade-in">
            <div className="px-4 py-3 space-y-1">
              {navItems.map(({ href, label, icon: Icon }) => {
                const isActive = pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 px-4 py-3 min-h-[44px] text-sm font-semibold uppercase tracking-wider transition-colors cursor-pointer font-display focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                      isActive
                        ? "bg-[var(--accent)] text-[var(--bg-primary)]"
                        : "text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]"
                    }`}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <Icon size={16} aria-hidden="true" />
                    {label}
                  </Link>
                );
              })}
            </div>

            {/* Mobile status */}
            <div className="px-4 py-3 border-t border-[var(--border-default)] flex items-center justify-between">
              <span className="font-mono text-xs text-[var(--text-muted)]">
                SYS {time}
              </span>
              <div className="flex items-center gap-2">
                <span className="status-dot status-dot-vacant" />
                <span className="font-mono text-xs text-[var(--vacant)]">LIVE</span>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
