import { ReactNode } from "react";

import { AdminShell } from "@/components/admin/AdminShell";
import { PortalGuard } from "@/components/os/PortalGuard";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="platform">
      <AdminShell>{children}</AdminShell>
    </PortalGuard>
  );
}
