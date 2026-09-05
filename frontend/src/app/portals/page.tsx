'use client';

import Link from 'next/link';

import { useCanonicalAuth } from '@/context/AuthContext';
import { availablePortals } from '@/lib/api/portal';

const COPY: Record<string, { kicker: string; body: string; limit?: string }> = {
  jobseeker: {
    kicker: 'Candidate OS',
    body: 'Work ID, career, opportunities, applications, interviews, and Athena.',
  },
  employer: {
    kicker: 'Employer OS',
    body: 'Company workspace, jobs, talent, pipeline, interviews, and Athena HR.',
  },
  government: {
    kicker: 'Government OS',
    body: 'Privacy-protected workforce intelligence. Aggregates only — no citizen records.',
  },
  admin: {
    kicker: 'Super Admin',
    body: 'Platform control plane. Only accounts with platform memberships can open this.',
  },
};

export default function PortalsPage() {
  const { me, logout } = useCanonicalAuth();
  const portals = availablePortals(me);

  return (
    <div className="min-h-screen bg-[#0b0c0d] px-6 py-16 text-white">
      <div className="mx-auto max-w-3xl">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-[#d4af37]">
          AskTrabaajo · Development
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Choose a portal</h1>
        <p className="mt-3 max-w-xl text-sm text-[#9ca3af]">
          Signed in as {me?.full_name || me?.email}. Each portal still asks the
          canonical API for permission. This screen does not bypass RBAC.
        </p>
        <div className="mt-10 grid gap-4">
          {portals.map((portal) => {
            const copy = COPY[portal.id];
            return (
              <Link
                key={portal.id}
                href={portal.href}
                className="rounded-xl border border-[#23272a] bg-[#111315] p-5 transition-colors hover:border-[#d4af37]/40"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#d4af37]">
                    {copy?.kicker ?? portal.label}
                  </p>
                  {copy?.limit && (
                    <span className="font-mono text-[10px] uppercase tracking-wider text-[#6b7280]">
                      {copy.limit}
                    </span>
                  )}
                </div>
                <h2 className="mt-2 text-xl font-semibold">{portal.label}</h2>
                <p className="mt-2 text-sm text-[#9ca3af]">{copy?.body}</p>
              </Link>
            );
          })}
        </div>
        <div className="mt-10 flex gap-4 text-sm text-[#9ca3af]">
          <Link href="/id" className="hover:text-white">
            Account
          </Link>
          <button
            type="button"
            onClick={() => void logout().then(() => { window.location.href = '/login'; })}
            className="hover:text-white"
          >
            Log out
          </button>
        </div>
      </div>
    </div>
  );
}
