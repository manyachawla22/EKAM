"use client";
import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";

export type Role = "organizer" | "judge" | "participant";

interface User {
  name: string;
  email: string;
  role: Role;
  avatar?: string;
  organization?: string;
}

interface AppState {
  user: User | null;
  theme: "dark" | "light";
  login: (user: User) => void;
  logout: () => void;
  toggleTheme: () => void;
  setTheme: (t: "dark" | "light") => void;
}

const AppContext = createContext<AppState | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [theme, setThemeState] = useState<"dark" | "light">("dark");

  const login = useCallback((u: User) => setUser(u), []);
  const logout = useCallback(() => setUser(null), []);
  const toggleTheme = useCallback(() => {
    setThemeState((t) => {
      const next = t === "dark" ? "light" : "dark";
      document.documentElement.classList.toggle("dark", next === "dark");
      return next;
    });
  }, []);
  const setTheme = useCallback((t: "dark" | "light") => {
    setThemeState(t);
    document.documentElement.classList.toggle("dark", t === "dark");
  }, []);

  return (
    <AppContext.Provider value={{ user, theme, login, logout, toggleTheme, setTheme }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppStore() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppStore must be used within AppProvider");
  return ctx;
}
