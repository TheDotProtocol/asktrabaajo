import { ReactNode } from "react";

import { GovernmentShell } from "@/components/government/GovernmentShell";
import { PortalGuard } from "@/components/os/PortalGuard";

export default function GovernmentLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="government">
      <GovernmentShell>{children}</GovernmentShell>
    </PortalGuard>
  );
}
