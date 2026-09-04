import { ReactNode } from "react";
import { OsChrome } from "@/components/os/OsChrome";
import { PortalGuard } from "@/components/os/PortalGuard";

const NAV = [
  { href: "/jobseeker", label: "Home" },
  { href: "/jobseeker/work-dna", label: "Work DNA" },
  { href: "/jobseeker/career", label: "Career" },
  { href: "/jobseeker/opportunities", label: "Opportunities" },
  { href: "/jobseeker/applications", label: "Applications" },
  { href: "/jobseeker/interviews", label: "Interviews" },
  { href: "/jobseeker/ai-interview", label: "AI Interview" },
  { href: "/jobseeker/interview-prep", label: "Interview Prep" },
  { href: "/jobseeker/offers", label: "Offers" },
  { href: "/jobseeker/communications", label: "Messages" },
  { href: "/id/work-id", label: "Work ID" },
];

export default function JobseekerLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="authenticated">
      <OsChrome
        portal="jobseeker"
        title="Career OS"
        accentClass="text-amber-500"
        nav={NAV}
      >
        {children}
      </OsChrome>
    </PortalGuard>
  );
}
