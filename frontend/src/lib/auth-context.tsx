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

function parseJwtExpiry(token: string): number | null {
  try {
    const payloadPart = token.split(".")[1];
    if (!payloadPart) {
      return null;
    }

    const base64 = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(window.atob(base64)) as { exp?: number };
    return typeof decoded.exp === "number" ? decoded.exp : null;
  } catch {
    return null;
  }
}

function tokenIsExpired(token: string): boolean {
  const expiry = parseJwtExpiry(token);
  if (!expiry) {
    return false;
  }
  return Date.now() >= expiry * 1000;
}

function clearStoredToken() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

function storeToken(token: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(() => {
    if (typeof window === "undefined") {
      return true;
    }

    const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    if (!token) {
      return false;
    }

    if (tokenIsExpired(token)) {
      clearStoredToken();
      return false;
    }

    return true;
  });
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
    if (!loading) {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      fetchCurrentUser()
        .then((currentUser) => {
          if (cancelled) {
            return;
          }
          setUser(currentUser);
          setError(null);
        })
        .catch((err) => {
          if (cancelled) {
            return;
          }
          clearStoredToken();
          setUser(null);
          setError(err instanceof Error ? err.message : "Session refresh failed");
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
  }, [loading]);

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
