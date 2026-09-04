import { ReactNode } from "react";
import { OsChrome } from "@/components/os/OsChrome";
import { PortalGuard } from "@/components/os/PortalGuard";

const NAV = [
  { href: "/id", label: "Account" },
  { href: "/id/work-id", label: "Work ID" },
  { href: "/jobseeker", label: "Career OS" },
];

export default function IdentityLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="authenticated">
      <OsChrome
        portal="jobseeker"
        title="Identity"
        accentClass="text-amber-500"
        nav={NAV}
      >
        {children}
      </OsChrome>
    </PortalGuard>
  );
}
