"use client";

// Edit an existing Employee Payroll Profile. RBAC-gated (UX only — the backend
// re-enforces write permission on save).

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PageHeader } from "@shared/components/PageHeader";
import { Loading, ErrorBanner } from "@shared/components/States";
import { useRoles } from "@shared/services/RolesContext";
import { canWriteProfiles } from "@shared/services/roles";
import { payrollApi } from "@shared/services/api";
import type { GovernmentEmployeePayrollProfile } from "@shared/types";
import { EmployeeForm } from "../../EmployeeForm";

export default function EditEmployeePage() {
  const params = useParams<{ name: string }>();
  const name = decodeURIComponent(params.name);
  const { roles } = useRoles();

  const [profile, setProfile] = useState<GovernmentEmployeePayrollProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    payrollApi.getEmployee(name).then(setProfile).catch((e: Error) => setError(e.message));
  }, [name]);

  return (
    <div>
      <PageHeader title="تعديل موظف" subtitle={name} />
      {!canWriteProfiles(roles) ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          ليس لديك صلاحية لتعديل الموظفين. هذه الصفحة للعرض فقط.
        </div>
      ) : error ? (
        <ErrorBanner message={error} />
      ) : profile === null ? (
        <Loading />
      ) : (
        <EmployeeForm mode="edit" initial={profile} />
      )}
    </div>
  );
}
