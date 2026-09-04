import Link from "next/link";
import { PageHeader, btnCls, cardCls, ghostBtnCls } from "@/components/candidate/ui";

export default function AthenaHrEntryPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Athena HR"
        title="Assistant entry"
        subtitle="Full Athena chat is Wave 4. This screen does not open a fake HR copilot or auto-confirm high-risk actions."
      />
      <section className={`${cardCls} border-[#d4af37]/25`}>
        <p className="text-sm text-[#9ca3af]">
          Use Talent Graph, pipeline, and analytics for hiring work today. When Athena is provisioned,
          confirmations will still require exact scope on the server.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/company/candidates" className={btnCls}>Open Talent Graph</Link>
          <Link href="/company" className={ghostBtnCls}>Command center</Link>
        </div>
      </section>
    </div>
  );
}
