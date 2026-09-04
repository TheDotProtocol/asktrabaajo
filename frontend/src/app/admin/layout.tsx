import { ReactNode } from "react";
import { OsChrome } from "@/components/os/OsChrome";
import { PortalGuard } from "@/components/os/PortalGuard";

const NAV = [
  { href: "/admin/governance", label: "Control Room", permission: "reports.read" },
  { href: "/admin/governance/enforcement", label: "Enforcement", permission: "enforcement.read" },
  { href: "/admin/governance/appeals", label: "Appeals", permission: "appeals.read" },
  { href: "/admin/governance/teams", label: "Teams", permission: "reports.teams" },
  { href: "/admin/governance/audit", label: "Audit Review", permission: "platform.audit.read" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="governance">
      <OsChrome
        portal="admin"
        title="Platform Governance"
        accentClass="text-indigo-500"
        nav={NAV}
      >
        {children}
      </OsChrome>
    </PortalGuard>
  );
}
