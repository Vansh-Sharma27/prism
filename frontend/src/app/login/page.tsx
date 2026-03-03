"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function sanitizeNextPath(nextPath: string | null): string {
  if (!nextPath || !nextPath.startsWith("/")) {
    return "/";
  }
  if (nextPath.startsWith("//")) {
    return "/";
  }
  return nextPath;
}

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated, loading, error: authError } = useAuth();

  const nextPath = useMemo(
    () => sanitizeNextPath(searchParams.get("next")),
    [searchParams]
  );

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string;
    password?: string;
  }>({});

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace(nextPath);
    }
  }, [isAuthenticated, loading, nextPath, router]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const nextFieldErrors: { email?: string; password?: string } = {};
    if (!EMAIL_RE.test(email.trim())) {
      nextFieldErrors.email = "Email address needs a valid format. Example: user@domain.com";
    }
    if (password.length < 8) {
      nextFieldErrors.password = "Password must be at least 8 characters.";
    }
    if (nextFieldErrors.email || nextFieldErrors.password) {
      setFieldErrors(nextFieldErrors);
      setError(null);
      return;
    }

    setSubmitting(true);
    setFieldErrors({});
    setError(null);

    try {
      await login(email.trim().toLowerCase(), password);
      router.replace(nextPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] hud-grid grain-overlay">
      <main id="main-content" className="mx-auto flex min-h-screen max-w-md items-center px-4 py-10 sm:px-6">
        <section className="w-full border border-[var(--border-default)] bg-[var(--bg-secondary)] p-6 sm:p-8">
          <div className="mb-6">
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">PRISM Auth</p>
            <h1 className="text-fluid-display-md mt-2 font-display font-semibold uppercase tracking-wider text-[var(--text-primary)] leading-[1.08]">
              Login
            </h1>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Authenticate to access live parking telemetry and admin controls.
            </p>
          </div>

          {(error || authError) && (
            <div className="mb-4 border border-[var(--warning)]/40 bg-[var(--warning)]/10 px-3 py-2 text-sm text-[var(--warning)]">
              {error || authError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="mb-1.5 block font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setFieldErrors((current) => ({ ...current, email: undefined }));
                }}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "login-email-error" : undefined}
                required
              />
              {fieldErrors.email && (
                <p id="login-email-error" className="mt-1 text-xs text-[var(--warning)]">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setFieldErrors((current) => ({ ...current, password: undefined }));
                }}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={fieldErrors.password ? "login-password-error" : undefined}
                required
                minLength={8}
              />
              {fieldErrors.password && (
                <p id="login-password-error" className="mt-1 text-xs text-[var(--warning)]">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={submitting || loading}
              className="flex w-full items-center justify-center gap-2 border border-[var(--accent)] bg-[var(--accent)] px-4 py-2 text-xs font-display font-semibold uppercase tracking-wider text-[var(--bg-primary)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {(submitting || loading) && (
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--bg-primary)]/50 border-t-[var(--bg-primary)]" />
              )}
              Sign In
            </button>
          </form>

          <p className="mt-4 text-sm text-[var(--text-muted)]">
            New user?{" "}
            <Link href="/register" className="text-[var(--accent)] underline-offset-2 hover:underline">
              Create an account
            </Link>
          </p>
        </section>
      </main>
    </div>
  );
}
