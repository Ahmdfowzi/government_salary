"use client";

// Provides the logged-in user's roles to the whole module (fetched once), for
// role-aware UI. Security is enforced by the backend; this only drives hide/disable.

import { createContext, useContext, useEffect, useState } from "react";
import { payrollApi } from "@shared/services/api";

interface RolesState {
  roles: string[];
  user: string;
  loading: boolean;
}

const RolesCtx = createContext<RolesState>({ roles: [], user: "", loading: true });

export function RolesProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<RolesState>({ roles: [], user: "", loading: true });

  useEffect(() => {
    payrollApi
      .currentUser()
      .then((r) => setState({ roles: r.roles ?? [], user: r.user ?? "", loading: false }))
      .catch(() => setState({ roles: [], user: "", loading: false }));
  }, []);

  return <RolesCtx.Provider value={state}>{children}</RolesCtx.Provider>;
}

export function useRoles(): RolesState {
  return useContext(RolesCtx);
}
