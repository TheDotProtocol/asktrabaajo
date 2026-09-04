import { ReactNode } from "react";
import { OsChrome } from "@/components/os/OsChrome";
import { PortalGuard } from "@/components/os/PortalGuard";

const NAV = [
  { href: "/company", label: "Home" },
  { href: "/company/jobs", label: "Jobs", permission: "jobs.view" },
  { href: "/company/pipeline", label: "Pipeline", permission: "applications.view" },
  { href: "/company/candidates", label: "Candidates", permission: "candidates.search" },
  { href: "/employer/ai-interviews", label: "AI Interviews", permission: "interviews.manage" },
  { href: "/employer/billing", label: "Billing", permission: "billing.read" },
];

export default function EmployerLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="authenticated">
      <OsChrome
        portal="company"
        title="Employer OS"
        accentClass="text-indigo-500"
        nav={NAV}
      >
        {children}
      </OsChrome>
    </PortalGuard>
  );
}
