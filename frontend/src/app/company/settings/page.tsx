"use client";

import Link from "next/link";

import { PageHeader, cardCls, ghostBtnCls, labelCls } from "@/components/candidate/ui";
import { useCanonicalAuth } from "@/context/AuthContext";
import { useOrg } from "@/context/OrgContext";

export default function CompanySettingsPage() {
  const { me } = useCanonicalAuth();
  const { membership, organizationId } = useOrg();

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Settings"
        title="Company settings"
        subtitle="Organization identity, members, billing, and security. Frontend links only — every change still goes through a canonical API."
      />
      <section className={cardCls}>
        <p className={labelCls}>Signed in</p>
        <p className="mt-2 text-lg font-medium">{me?.full_name}</p>
        <p className="text-sm text-[#9ca3af]">{me?.email}</p>
        <p className="mt-2 text-xs text-[#6b7280]">
          Org role {membership?.role ?? "none"} · organization {organizationId || "not selected"}
        </p>
      </section>
      <section className="grid gap-3 sm:grid-cols-2">
        {[
          { href: "/company/profile", title: "Company profile", body: "Name, industry, HQ city/country." },
          { href: "/company/members", title: "Members & RBAC", body: "Invite existing accounts and change org roles." },
          { href: "/employer/billing", title: "Billing", body: "Plan, entitlements, invoices. Mock provider — no real charges." },
          { href: "/id", title: "Account security", body: "Password, sessions, email verification." },
        ].map((item) => (
          <Link key={item.href} href={item.href} className={cardCls}>
            <p className="font-medium">{item.title}</p>
            <p className="mt-1 text-sm text-[#9ca3af]">{item.body}</p>
          </Link>
        ))}
      </section>
      <Link href="/company" className={ghostBtnCls}>Back to command center</Link>
    </div>
  );
}
