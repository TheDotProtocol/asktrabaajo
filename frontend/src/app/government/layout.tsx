import { ReactNode } from "react";
import Link from "next/link";

import { PortalGuard } from "@/components/os/PortalGuard";
import { PortalSwitchLinks } from "@/components/os/PortalSwitchLinks";

export default function GovernmentLayout({ children }: { children: ReactNode }) {
  return (
    <PortalGuard allow="government">
      <div className="candidate-os min-h-screen bg-[#0b0c0d] text-white">
        <header className="border-b border-[#23272a] px-6 py-4">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
            <Link href="/government" className="text-lg font-semibold tracking-tight">
              Ask<span className="text-[#d4af37]">Trabaajo</span>
              <span className="ml-2 text-sm font-normal text-[#9ca3af]">· Government</span>
            </Link>
            <PortalSwitchLinks compact />
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
      </div>
    </PortalGuard>
  );
}
