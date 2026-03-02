"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, loading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, loading, router]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const normalizedEmail = email.trim().toLowerCase();

    if (!EMAIL_RE.test(normalizedEmail)) {
      setError("Enter a valid email address.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Password and confirm password do not match.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await register(normalizedEmail, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
            <h1 className="mt-2 font-display text-2xl font-semibold uppercase tracking-wider text-[var(--text-primary)]">
              Register
            </h1>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Create a new account for secured access to PRISM dashboards.
            </p>
          </div>

          {error && (
            <div className="mb-4 border border-[var(--warning)]/40 bg-[var(--warning)]/10 px-3 py-2 text-sm text-[var(--warning)]">
              {error}
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
                onChange={(event) => setEmail(event.target.value)}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
                required
                minLength={8}
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="mb-1.5 block font-display text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
                required
                minLength={8}
              />
            </div>

            <button
              type="submit"
              disabled={submitting || loading}
              className="flex w-full items-center justify-center gap-2 border border-[var(--accent)] bg-[var(--accent)] px-4 py-2 text-xs font-display font-semibold uppercase tracking-wider text-[var(--bg-primary)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {(submitting || loading) && (
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--bg-primary)]/50 border-t-[var(--bg-primary)]" />
              )}
              Create Account
            </button>
          </form>

          <p className="mt-4 text-sm text-[var(--text-muted)]">
            Already have an account?{" "}
            <Link href="/login" className="text-[var(--accent)] underline-offset-2 hover:underline">
              Login
            </Link>
          </p>
        </section>
      </main>
    </div>
  );
}
