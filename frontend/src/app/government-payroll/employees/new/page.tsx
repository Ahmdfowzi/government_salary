"use client";

// Create a new Employee Payroll Profile. RBAC-gated (UX only — the backend
// re-enforces create permission on save).

import { PageHeader } from "@shared/components/PageHeader";
import { useRoles } from "@shared/services/RolesContext";
import { canWriteProfiles } from "@shared/services/roles";
import { EmployeeForm } from "../EmployeeForm";

export default function NewEmployeePage() {
  const { roles } = useRoles();

  return (
    <div>
      <PageHeader title="إضافة موظف" subtitle="إنشاء ملف راتبي لموظف جديد" />
      {canWriteProfiles(roles) ? (
        <EmployeeForm mode="create" />
      ) : (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          ليس لديك صلاحية لإنشاء أو تعديل الموظفين. هذه الصفحة للعرض فقط.
        </div>
      )}
    </div>
  );
}
