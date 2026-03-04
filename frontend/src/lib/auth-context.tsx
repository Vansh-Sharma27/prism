"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  AUTH_SESSION_INVALID_EVENT,
  AUTH_TOKEN_STORAGE_KEY,
  fetchCurrentUser,
  loginUser,
  registerUser,
  type AuthUser,
} from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const JWT_EXPIRY_SKEW_MS = 30_000;

function parseJwtExpiry(token: string): number | null {
  try {
    const payloadPart = token.split(".")[1];
    if (!payloadPart) {
      return null;
    }

    const base64 = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const padding = "=".repeat((4 - (base64.length % 4)) % 4);
    const decoded = JSON.parse(window.atob(`${base64}${padding}`)) as { exp?: number };
    return typeof decoded.exp === "number" ? decoded.exp : null;
  } catch {
    return null;
  }
}

function tokenIsExpired(token: string): boolean {
  const expiry = parseJwtExpiry(token);
  if (!expiry) {
    return true;
  }
  return Date.now() >= expiry * 1000 - JWT_EXPIRY_SKEW_MS;
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function clearStoredToken() {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage failures; user will still be treated as logged out.
  }
}

function storeToken(token: string) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore storage failures; in-memory auth state still updates.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  // Keep initial state deterministic across server and client to avoid hydration mismatch.
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshSession = useCallback(async () => {
    try {
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
      setError(null);
    } catch (err) {
      clearStoredToken();
      setUser(null);
      setError(err instanceof Error ? err.message : "Session refresh failed");
      throw err;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const finishAsLoggedOut = (nextError: string | null) => {
      clearStoredToken();
      if (!cancelled) {
        setUser(null);
        setError(nextError);
        setLoading(false);
      }
    };

    const timer = window.setTimeout(() => {
      const token = getStoredToken();
      if (!token || tokenIsExpired(token)) {
        finishAsLoggedOut(null);
        return;
      }

      fetchCurrentUser()
        .then((currentUser) => {
          if (cancelled) {
            return;
          }
          setUser(currentUser);
          setError(null);
        })
        .catch((err) => {
          finishAsLoggedOut(err instanceof Error ? err.message : "Session refresh failed");
        })
        .finally(() => {
          if (!cancelled) {
            setLoading(false);
          }
        });
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    const handleSessionInvalid = () => {
      clearStoredToken();
      setUser(null);
      setError("Session expired. Please login again.");
      setLoading(false);
    };

    window.addEventListener(AUTH_SESSION_INVALID_EVENT, handleSessionInvalid);
    return () => {
      window.removeEventListener(AUTH_SESSION_INVALID_EVENT, handleSessionInvalid);
    };
  }, []);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== AUTH_TOKEN_STORAGE_KEY) {
        return;
      }

      const nextToken = event.newValue;
      if (!nextToken || tokenIsExpired(nextToken)) {
        clearStoredToken();
        setUser(null);
        setError(null);
        setLoading(false);
        return;
      }

      void refreshSession().catch(() => {
        // refreshSession already handles local state updates on failure.
      });
    };

    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener("storage", handleStorage);
    };
  }, [refreshSession]);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginUser({ email, password });
    storeToken(result.accessToken);
    setUser(result.user);
    setError(null);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    await registerUser({ email, password });
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
    setError(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      isAuthenticated: Boolean(user),
      login,
      register,
      logout,
      refreshSession,
    }),
    [error, loading, login, logout, refreshSession, register, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
