/**
 * Platform Governance shell (Phase 9 proof).
 *
 * Separate from the employer HR interface by construction: these routes are
 * platform-scoped (reports.read & friends) and render only governance data —
 * never private Work ID sections or documents. The final Super Admin Portal
 * replaces this shell later.
 */
import Link from "next/link";
import { ReactNode } from "react";

const NAV = [
  { href: "/admin/governance", label: "Control Room", exact: false },
  { href: "/admin/governance/teams", label: "Teams", exact: false },
  { href: "/admin/governance/audit", label: "Audit Review", exact: false },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/90 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/admin/governance" className="text-sm font-semibold tracking-tight">
            <span className="text-indigo-500">AskTrabaajo</span>{" "}
            <span className="text-neutral-400">· Platform Governance</span>
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
              href="/company"
              className="rounded px-2.5 py-1 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
            >
              Company ↗
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
