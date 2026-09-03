/**
 * Company / Employer Employment OS shell (Phase 6 functional proof).
 *
 * NOT the final product UI — the Figma design system replaces this shell
 * later. Its job is to prove the employer workflows end-to-end through the
 * typed API client, behind the canonical tenancy/RBAC model.
 */
import Link from "next/link";
import { ReactNode } from "react";

const NAV = [
  { href: "/company", label: "Home", exact: true },
  { href: "/company/jobs", label: "Jobs" },
  { href: "/company/pipeline", label: "Pipeline" },
];

export default function CompanyLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/90 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/company" className="text-sm font-semibold tracking-tight">
            <span className="text-indigo-500">AskTrabaajo</span>{" "}
            <span className="text-neutral-400">· Employer OS</span>
          </Link>
          <nav className="flex flex-wrap items-center gap-1 text-sm">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded px-2.5 py-1 text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-300 dark:hover:bg-neutral-800 dark:hover:text-white"
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/jobseeker"
              className="rounded px-2.5 py-1 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
            >
              Jobseeker ↗
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
