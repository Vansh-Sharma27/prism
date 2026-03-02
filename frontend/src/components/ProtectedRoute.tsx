"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, type ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";

type UserRole = "student" | "faculty" | "admin";

interface ProtectedRouteProps {
  children: ReactNode;
  requireRole?: UserRole;
}

function LoadingGate({ label }: { label: string }) {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <main className="mx-auto flex min-h-screen max-w-lg items-center justify-center px-4">
        <div className="w-full border border-[var(--border-default)] bg-[var(--bg-secondary)] p-8 text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-[var(--border-default)] border-t-[var(--accent)]" />
          <h1 className="font-display text-lg font-semibold uppercase tracking-wider text-[var(--text-primary)]">
            {label}
          </h1>
          <p className="mt-2 text-sm text-[var(--text-muted)]">Please wait...</p>
        </div>
      </main>
    </div>
  );
}

export function ProtectedRoute({ children, requireRole }: ProtectedRouteProps) {
  const { user, loading, isAuthenticated, logout } = useAuth();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();

  const nextPath = useMemo(() => {
    const query = searchParams.toString();
    return query ? `${pathname}?${query}` : pathname;
  }, [pathname, searchParams]);

  useEffect(() => {
    if (loading || isAuthenticated) {
      return;
    }

    router.replace(`/login?next=${encodeURIComponent(nextPath)}`);
  }, [isAuthenticated, loading, nextPath, router]);

  if (loading) {
    return <LoadingGate label="Validating Session" />;
  }

  if (!isAuthenticated) {
    return <LoadingGate label="Redirecting To Login" />;
  }

  if (requireRole && user?.role !== requireRole) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
        <main className="mx-auto flex min-h-screen max-w-lg items-center justify-center px-4">
          <div className="w-full border border-[var(--warning)]/40 bg-[var(--bg-secondary)] p-8">
            <h1 className="font-display text-lg font-semibold uppercase tracking-wider text-[var(--warning)]">
              Access Denied
            </h1>
            <p className="mt-3 text-sm text-[var(--text-secondary)]">
              This page requires <span className="font-mono uppercase">{requireRole}</span> access.
            </p>
            <div className="mt-6 flex items-center gap-3">
              <Link
                href="/"
                className="border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2 text-xs font-display font-semibold uppercase tracking-wider text-[var(--text-primary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
              >
                Back To Dashboard
              </Link>
              <button
                type="button"
                onClick={logout}
                className="border border-[var(--warning)]/50 px-4 py-2 text-xs font-display font-semibold uppercase tracking-wider text-[var(--warning)] transition-colors hover:bg-[var(--warning)]/10"
              >
                Sign Out
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return <>{children}</>;
}
