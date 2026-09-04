"use client";

import { PageHeader, cardCls } from "@/components/candidate/ui";

export default function GovernmentInvestmentPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Investment"
        title="Expansion intelligence"
        subtitle="FUTURE CAPABILITY. No investors, programs, or expansion requests are stored."
      />
      <div className={cardCls}>
        <p className="text-sm text-[#9ca3af] leading-relaxed">
          A later wave may let an authorized employer describe an expansion intent and
          let government inspect the same aggregate workforce landscape already
          available in Command Center — skills, opportunity volume, and regional
          talent — without inventing investment amounts or government programs.
        </p>
        <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.16em] text-[#d4af37]">
          Not implemented
        </p>
      </div>
    </div>
  );
}
