"use client";

// Provides the logged-in user's roles + auth state to the whole module, for
// role-aware UI and the login gate. Security is enforced by the backend; this
// only drives hide/disable and whether to show the login form.

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { payrollApi } from "@shared/services/api";

interface RolesState {
  roles: string[];
  user: string;
  loading: boolean;
  authenticated: boolean;
  refresh: () => Promise<void>;
}

const RolesCtx = createContext<RolesState>({
  roles: [],
  user: "",
  loading: true,
  authenticated: false,
  refresh: async () => {},
});

export function RolesProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<Omit<RolesState, "refresh">>({
    roles: [],
    user: "",
    loading: true,
    authenticated: false,
  });

  // current_user is whitelisted but NOT allow_guest, so it 403s until the user
  // has a session — which is exactly how we detect "not logged in".
  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }));
    try {
      const r = await payrollApi.currentUser();
      const authenticated = !!r.user && r.user !== "Guest";
      setState({ roles: r.roles ?? [], user: r.user ?? "", loading: false, authenticated });
    } catch {
      setState({ roles: [], user: "", loading: false, authenticated: false });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return <RolesCtx.Provider value={{ ...state, refresh }}>{children}</RolesCtx.Provider>;
}

export function useRoles(): RolesState {
  return useContext(RolesCtx);
}
