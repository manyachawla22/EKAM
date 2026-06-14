"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { onAuthStateChanged, auth, type FirebaseUser } from "./firebase";
import { loginUser, getMe, setEkamToken, getEkamToken, setSessionKind, getSessionKind } from "./api";
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
      // Login failed (expired/revoked Firebase session, backend rejected the
      // token, etc.). Clear any stale EKAM token and treat the user as logged
      // out rather than leaving a half-authenticated state that keeps retrying.
      console.warn("Could not sync profile with backend; treating as signed out:", err);
      setEkamToken(null);
      setProfile(null);
    }
  }, []);

  // Load profile for participant/judge who only have an EKAM JWT (no Firebase)
  const syncEkamOnlyProfile = useCallback(async () => {
    try {
      const backendUser = await getMe();
      setProfile(backendUser);
    } catch (err) {
      // Only treat an actual auth rejection (401/403) as "logged out" and clear
      // the EKAM token. A transient failure (timeout, 500, backend reloading,
      // DB pool blip) must NOT wipe the token: doing so drops the participant/
      // judge session, and since Firebase auth is shared across all tabs while
      // the EKAM token is per-tab, the next request silently falls back to the
      // organizer's Firebase identity — i.e. participant/judge actions get sent
      // as the organizer. On a transient error, keep the token (and any existing
      // profile); a later refresh/poll recovers it.
      const msg = err instanceof Error ? err.message : "";
      if (/\((401|403)\)/.test(msg)) {
        setProfile(null);
        setEkamToken(null);
        setSessionKind(null);
      }
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    // An EKAM (participant/judge) tab must always refresh via its own session,
    // even if `user` still holds a shared organizer Firebase identity — otherwise
    // syncProfile→loginUser would overwrite this tab's EKAM token with the org's.
    if (getSessionKind() === "ekam") {
      setUser(null);
      if (getEkamToken()) {
        await syncEkamOnlyProfile();
      } else {
        setProfile(null);
      }
    } else if (user) {
      await syncProfile(user);
    } else if (getEkamToken()) {
      await syncEkamOnlyProfile();
    }
  }, [user, syncProfile, syncEkamOnlyProfile]);

  const clearAuth = useCallback(() => {
    setUser(null);
    setProfile(null);
    setEkamToken(null);
    setSessionKind(null);
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      // CRITICAL for shared browsers: Firebase auth is shared across all tabs, so
      // this listener fires with the *organizer's* Firebase user even inside a
      // participant/judge tab. If we let that through, syncProfile→loginUser would
      // overwrite this tab's EKAM token with the organizer's and hijack the
      // session. A tab that logged in as a participant/judge (kind "ekam") must
      // ignore Firebase entirely and stay on its per-tab EKAM session.
      if (getSessionKind() === "ekam") {
        setUser(null);
        if (getEkamToken()) {
          await syncEkamOnlyProfile();
        } else {
          setProfile(null);
        }
        setLoading(false);
        return;
      }

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
