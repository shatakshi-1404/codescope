import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { authApi, authStorage, refreshSession, setAuthFailureHandler } from "../lib/api";
import type { User } from "../lib/types";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthValue {
  user: User | null;
  status: Status;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  // Restore the session on page load using the stored refresh token.
  useEffect(() => {
    let active = true;
    (async () => {
      if (!authStorage.hasRefreshToken()) {
        setStatus("anonymous");
        return;
      }
      const session = await refreshSession();
      if (!active) return;
      if (session) {
        setUser(session.user);
        setStatus("authenticated");
      } else {
        setStatus("anonymous");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // If the API client ever concludes the session is dead, drop to anonymous.
  useEffect(() => {
    setAuthFailureHandler(() => {
      setUser(null);
      setStatus("anonymous");
      queryClient.clear();
    });
    return () => setAuthFailureHandler(null);
  }, [queryClient]);

  const login = useCallback(async (email: string, password: string) => {
    const u = await authApi.login(email, password);
    setUser(u);
    setStatus("authenticated");
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const u = await authApi.register(name, email, password);
    setUser(u);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    setStatus("anonymous");
    queryClient.clear(); // never leave one user's cached data around for the next
  }, [queryClient]);

  const value = useMemo(
    () => ({ user, status, login, register, logout }),
    [user, status, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
