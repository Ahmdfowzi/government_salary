import { Sidebar } from "@shared/layouts/Sidebar";
import { AuthGate } from "@shared/layouts/AuthGate";
import { RolesProvider } from "@shared/services/RolesContext";

export default function GovernmentPayrollLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RolesProvider>
      <AuthGate>
        <div className="flex min-h-screen bg-slate-50">
          <Sidebar />
          <main className="flex-1 p-6 lg:p-8">{children}</main>
        </div>
      </AuthGate>
    </RolesProvider>
  );
}
