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
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string;
    password?: string;
    confirmPassword?: string;
  }>({});

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, loading, router]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const normalizedEmail = email.trim().toLowerCase();
    const nextFieldErrors: {
      email?: string;
      password?: string;
      confirmPassword?: string;
    } = {};

    if (!EMAIL_RE.test(normalizedEmail)) {
      nextFieldErrors.email = "Email address needs a valid format. Example: user@domain.com";
    }

    if (password.length < 8) {
      nextFieldErrors.password = "Password must be at least 8 characters.";
    }

    if (password !== confirmPassword) {
      nextFieldErrors.confirmPassword = "Confirm password must match password.";
    }

    if (
      nextFieldErrors.email ||
      nextFieldErrors.password ||
      nextFieldErrors.confirmPassword
    ) {
      setFieldErrors(nextFieldErrors);
      setError(null);
      return;
    }

    setSubmitting(true);
    setFieldErrors({});
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
            <h1 className="text-fluid-display-md mt-2 font-display font-semibold uppercase tracking-wider text-[var(--text-primary)] leading-[1.08]">
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
                onChange={(event) => {
                  setEmail(event.target.value);
                  setFieldErrors((current) => ({ ...current, email: undefined }));
                }}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "register-email-error" : undefined}
                required
              />
              {fieldErrors.email && (
                <p id="register-email-error" className="mt-1 text-xs text-[var(--warning)]">
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
                autoComplete="new-password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setFieldErrors((current) => ({ ...current, password: undefined }));
                }}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={fieldErrors.password ? "register-password-error" : undefined}
                required
                minLength={8}
              />
              {fieldErrors.password && (
                <p id="register-password-error" className="mt-1 text-xs text-[var(--warning)]">
                  {fieldErrors.password}
                </p>
              )}
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
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                  setFieldErrors((current) => ({
                    ...current,
                    confirmPassword: undefined,
                  }));
                }}
                className="w-full border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
                aria-invalid={Boolean(fieldErrors.confirmPassword)}
                aria-describedby={
                  fieldErrors.confirmPassword ? "register-confirm-password-error" : undefined
                }
                required
                minLength={8}
              />
              {fieldErrors.confirmPassword && (
                <p
                  id="register-confirm-password-error"
                  className="mt-1 text-xs text-[var(--warning)]"
                >
                  {fieldErrors.confirmPassword}
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
