import Link from "next/link";
import { PageHeader, btnCls, cardCls, ghostBtnCls } from "@/components/candidate/ui";

export default function AthenaEntryPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Athena"
        title="Assistant entry"
        subtitle="Full Athena chat is a later wave. The Career Advisor already uses your real Work ID — it does not invent recommendations in the browser."
      />
      <section className={`${cardCls} border-[#d4af37]/25`}>
        <p className="text-sm text-[#9ca3af]">
          AI_PROVIDER is currently in degraded/safe mode unless an operator has configured it.
          High-risk actions still require exact confirmation on the server. This screen does not
          open a fake chat.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/jobseeker/career" className={btnCls}>
            Open Career Advisor
          </Link>
          <Link href="/jobseeker" className={ghostBtnCls}>
            Back to command surface
          </Link>
        </div>
      </section>
    </div>
  );
}
