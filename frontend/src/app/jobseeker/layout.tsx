/**
 * Jobseeker Career OS shell (Phase 5 functional proof).
 *
 * This is NOT the final product UI — the Figma design system replaces this
 * shell later. Its job is to prove the career workflows end-to-end through
 * the typed API client, with a calm, readable structure.
 */
import Link from "next/link";
import { ReactNode } from "react";

const NAV = [
  { href: "/jobseeker", label: "Home", exact: true },
  { href: "/jobseeker/work-dna", label: "Work DNA" },
  { href: "/jobseeker/career", label: "Career" },
  { href: "/jobseeker/opportunities", label: "Opportunities" },
  { href: "/jobseeker/applications", label: "Applications" },
  { href: "/jobseeker/interviews", label: "Interviews" },
  { href: "/jobseeker/offers", label: "Offers" },
  { href: "/jobseeker/communications", label: "Messages" },
];

export default function JobseekerLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/90 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/jobseeker" className="text-sm font-semibold tracking-tight">
            <span className="text-amber-500">AskTrabaajo</span>{" "}
            <span className="text-neutral-400">· Career OS</span>
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
              href="/id"
              className="rounded px-2.5 py-1 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
            >
              Identity ↗
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
