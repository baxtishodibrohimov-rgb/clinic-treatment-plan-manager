"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, login as apiLogin, setToken } from "./api";
import type { UserOut } from "./types";

interface AuthContextValue {
  user: UserOut | null;
  loading: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refresh = async () => {
    try {
      const me = await api.get<UserOut>("/api/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
    // Deliberately runs once on mount only.
  }, []);

  const login = async (email: string, password: string) => {
    const token = await apiLogin(email, password);
    setToken(token);
    await refresh();
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    router.push("/login");
  };

  const isAdmin = !!user?.roles.some((r) => r === "admin" || r === "super_admin");

  return <AuthContext.Provider value={{ user, loading, isAdmin, login, logout, refresh }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
