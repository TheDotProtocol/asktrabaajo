import { ReactNode } from "react";
import { EmployerShell } from "@/components/employer/EmployerShell";
import { PortalGuard } from "@/components/os/PortalGuard";

export default function CompanyLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="authenticated">
      <EmployerShell>{children}</EmployerShell>
    </PortalGuard>
  );
}
