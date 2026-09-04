'use client';

import Link from 'next/link';

import { useCanonicalAuth } from '@/context/AuthContext';
import { availablePortals } from '@/lib/api/portal';

export function PortalSwitchLinks({ compact = false }: { compact?: boolean }) {
  const { me } = useCanonicalAuth();
  const portals = availablePortals(me);
  if (portals.length < 2) return null;

  if (compact) {
    return (
      <Link href="/portals" className="text-xs text-[#d4af37] hover:underline">
        Switch portal
      </Link>
    );
  }

  return (
    <nav aria-label="Portals" className="flex flex-wrap gap-2">
      {portals.map((portal) => (
        <Link
          key={portal.id}
          href={portal.href}
          className="rounded border border-[#23272a] px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-[#9ca3af] hover:border-[#d4af37]/40 hover:text-[#d4af37]"
        >
          {portal.label}
        </Link>
      ))}
    </nav>
  );
}
