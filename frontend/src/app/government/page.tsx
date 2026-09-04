'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { PageHeader, cardCls } from '@/components/candidate/ui';
import { useCanonicalAuth } from '@/context/AuthContext';
import { governmentMemberships } from '@/lib/api/portal';
import { api } from '@/lib/api/session';
import { AthenaStatus } from '@/lib/api/types';

export default function GovernmentFoundationPage() {
  const { me } = useCanonicalAuth();
  const memberships = governmentMemberships(me);
  const [status, setStatus] = useState<AthenaStatus | null>(null);
  const [modes, setModes] = useState<string[]>([]);

  useEffect(() => {
    api.get<AthenaStatus>('/athena/status').then(setStatus).catch(() => setStatus(null));
    api.get<string[]>('/athena/modes').then(setModes).catch(() => setModes([]));
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Government · foundation"
        title="Workforce intelligence is not implemented"
        subtitle="AskTrabaajo government access is aggregate-only by architecture. This page does not invent citizen records, ministry integrations, or fake labour-market statistics."
      />

      <div className={cardCls}>
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#d4af37]">
          Membership
        </p>
        {memberships.length === 0 ? (
          <p className="mt-3 text-sm text-[#9ca3af]">No government organization on this account.</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm text-[#e5e7eb]">
            {memberships.map((row) => (
              <li key={row.organization_id}>
                {row.organization_name} · {row.role.replaceAll('_', ' ')}
                <span className="ml-2 font-mono text-[10px] uppercase text-[#6b7280]">DEV</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className={cardCls}>
        <p className="text-xl font-semibold text-white">What exists today</p>
        <ul className="mt-4 space-y-2 text-sm text-[#9ca3af]">
          <li>Canonical roles <code className="text-[#e5e7eb]">government_admin</code> and <code className="text-[#e5e7eb]">government_user</code>.</li>
          <li>Permission <code className="text-[#e5e7eb]">workforce.aggregates.read</code> — catalog only. No aggregate API is registered.</li>
          <li>
            Athena government mode is eligible
            {modes.includes('government') ? ' for this account' : ''}
            {status?.available ? '' : ' and remains architecture-only (no tools, no fabricated replies).'}
          </li>
        </ul>
      </div>

      <div className={cardCls}>
        <p className="text-xl font-semibold text-white">Deliberately not built</p>
        <ul className="mt-4 space-y-2 text-sm text-[#9ca3af]">
          <li>Citizen lookup, employment records, or individual Work ID access for government.</li>
          <li>Country / state / city intelligence dashboards.</li>
          <li>Skill-shortage charts, investment views, or ministry workflows.</li>
        </ul>
        <p className="mt-4 text-sm text-[#6b7280]">
          Those Figma frames remain design. Wave 7 only makes this foundation visible.
        </p>
      </div>

      <Link href="/portals" className="inline-block text-sm text-[#d4af37] hover:underline">
        Back to portals
      </Link>
    </div>
  );
}
