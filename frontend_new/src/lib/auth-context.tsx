"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { onAuthStateChanged, auth, type FirebaseUser } from "./firebase";
import { loginUser, getMe, setEkamToken, getEkamToken } from "./api";
import type { User, UserRole } from "@/types";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: FirebaseUser | null;
  profile: User | null;
  loading: boolean;
  role: UserRole | null;
  refreshProfile: () => Promise<void>;
  clearAuth: () => void;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ─── Pending signup intent ────────────────────────────────────────────────────
// When the user clicks "Sign Up", we stash the chosen role here. The auth-state
// listener picks it up so the first /auth/login call after Firebase signup
// includes the role.
const PENDING_ROLE_KEY = "ekam:pending-signup-role";
const PENDING_NAME_KEY = "ekam:pending-signup-name";

export function stashPendingSignup(role?: UserRole, name?: string) {
  if (typeof window === "undefined") return;
  if (role) sessionStorage.setItem(PENDING_ROLE_KEY, role);
  if (name) sessionStorage.setItem(PENDING_NAME_KEY, name);
}

function popPendingSignup(): { role?: UserRole; name?: string } {
  if (typeof window === "undefined") return {};
  const role = sessionStorage.getItem(PENDING_ROLE_KEY) as UserRole | null;
  const name = sessionStorage.getItem(PENDING_NAME_KEY);
  sessionStorage.removeItem(PENDING_ROLE_KEY);
  sessionStorage.removeItem(PENDING_NAME_KEY);
  return {
    role: role || undefined,
    name: name || undefined,
  };
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<FirebaseUser | null>(null);
  const [profile, setProfile] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const syncProfile = useCallback(async (firebaseUser: FirebaseUser) => {
    try {
      const pending = popPendingSignup();
      const backendUser = await loginUser({
        name: pending.name || firebaseUser.displayName || undefined,
        role: pending.role,
      });
      setProfile(backendUser);
    } catch (err) {
      console.error("Failed to sync profile with backend:", err);
      setProfile(null);
    }
  }, []);

  // Load profile for participant/judge who only have an EKAM JWT (no Firebase)
  const syncEkamOnlyProfile = useCallback(async () => {
    try {
      const backendUser = await getMe();
      setProfile(backendUser);
    } catch {
      // Token expired or invalid — clear it so the user sees the login page
      setProfile(null);
      setEkamToken(null);
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (user) {
      await syncProfile(user);
    } else if (getEkamToken()) {
      await syncEkamOnlyProfile();
    }
  }, [user, syncProfile, syncEkamOnlyProfile]);

  const clearAuth = useCallback(() => {
    setUser(null);
    setProfile(null);
    setEkamToken(null);
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        await syncProfile(firebaseUser);
      } else {
        // No Firebase session — check for an existing EKAM JWT
        // (participants and judges never have a Firebase account)
        const ekamToken = getEkamToken();
        if (ekamToken) {
          await syncEkamOnlyProfile();
        } else {
          setProfile(null);
        }
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, [syncProfile, syncEkamOnlyProfile]);

  const role = profile?.role ?? null;

  return (
    <AuthContext.Provider
      value={{ user, profile, loading, role, refreshProfile, clearAuth }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export type { AuthContextValue };
