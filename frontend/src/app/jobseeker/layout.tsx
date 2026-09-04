import { ReactNode } from "react";
import { CandidateShell } from "@/components/candidate/CandidateShell";
import { PortalGuard } from "@/components/os/PortalGuard";

export default function JobseekerLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="authenticated">
      <CandidateShell>{children}</CandidateShell>
    </PortalGuard>
  );
}
