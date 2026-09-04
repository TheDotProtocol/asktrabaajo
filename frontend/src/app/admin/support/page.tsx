"use client";

import Link from "next/link";

import { PageHeader, cardCls, ghostBtnCls } from "@/components/candidate/ui";
import { useCanonicalAuth } from "@/context/AuthContext";
import { hasPermission } from "@/lib/api/portal";

export default function AdminSupportPage() {
  const { me } = useCanonicalAuth();
  const canReadCases = hasPermission(me, "reports.read");

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Platform support"
        title="Customer and tech support"
        subtitle="Support works through authorized operational cases. There is no unrestricted customer-360 API and no ticket product in this release."
      />
      <div className={cardCls}>
        <p className="font-medium text-white">Case-linked access only</p>
        <p className="mt-2 text-sm text-[#9ca3af]">
          The Figma Customer Support and Tech Support consoles assume a ticket directory and
          user diagnostics APIs that do not exist. Those screens are foundation-only.
          Operators with <code className="text-[#d4af37]">reports.read</code> review governance
          cases. Operators with <code className="text-[#d4af37]">sessions.manage</code> can
          manage their own sessions from Settings. Private Work ID content is never exposed here.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          {canReadCases ? (
            <Link href="/admin/governance" className={ghostBtnCls}>
              Open governance cases
            </Link>
          ) : (
            <p className="text-sm text-[#6b7280]">This account cannot read the governance queue.</p>
          )}
          <Link href="/admin/settings" className={ghostBtnCls}>
            Account and sessions
          </Link>
        </div>
      </div>
    </div>
  );
}
