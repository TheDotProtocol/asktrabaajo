'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { getStoredOrganizationId, setStoredOrganizationId } from '@/lib/api/org';
import { employerMemberships } from '@/lib/api/portal';
import { MembershipBrief } from '@/lib/api/types';
import { useCanonicalAuth } from '@/context/AuthContext';

interface OrgContextValue {
  organizationId: string;
  membership: MembershipBrief | null;
  memberships: MembershipBrief[];
  selectOrganization: (organizationId: string) => void;
}

const OrgContext = createContext<OrgContextValue | null>(null);

export function OrgProvider({ children }: { children: ReactNode }) {
  const { me } = useCanonicalAuth();
  const memberships = useMemo(() => employerMemberships(me), [me]);
  const [organizationId, setOrganizationId] = useState('');

  useEffect(() => {
    if (memberships.length === 0) {
      setOrganizationId('');
      return;
    }
    const stored = getStoredOrganizationId();
    const match =
      memberships.find((m) => m.organization_id === stored) ?? memberships[0];
    setOrganizationId(match.organization_id);
    setStoredOrganizationId(match.organization_id);
  }, [memberships]);

  const selectOrganization = useCallback(
    (id: string) => {
      const match = memberships.find((m) => m.organization_id === id);
      if (!match) return;
      setOrganizationId(match.organization_id);
      setStoredOrganizationId(match.organization_id);
    },
    [memberships]
  );

  const membership = memberships.find((m) => m.organization_id === organizationId) ?? null;

  const value = useMemo(
    () => ({
      organizationId,
      membership,
      memberships,
      selectOrganization,
    }),
    [organizationId, membership, memberships, selectOrganization]
  );

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
}

export function useOrg(): OrgContextValue {
  const ctx = useContext(OrgContext);
  if (!ctx) {
    throw new Error('useOrg must be used within OrgProvider');
  }
  return ctx;
}
