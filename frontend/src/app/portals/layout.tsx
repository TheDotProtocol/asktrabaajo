import { ReactNode } from "react";

import { PortalGuard } from "@/components/os/PortalGuard";

export default function PortalsLayout({ children }: { children: ReactNode }) {
  return <PortalGuard allow="authenticated">{children}</PortalGuard>;
}
