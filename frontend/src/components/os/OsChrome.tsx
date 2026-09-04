'use client';

import Link from 'next/link';
import { ReactNode } from 'react';
import { useCanonicalAuth } from '@/context/AuthContext';
import { useOrg } from '@/context/OrgContext';
import {
  canAccessPlatform,
  hasPermission,
} from '@/lib/api/portal';

export interface OsNavItem {
  href: string;
  label: string;
  permission?: string;
}

interface OsChromeProps {
  portal: 'jobseeker' | 'company' | 'admin';
  title: string;
  accentClass: string;
  nav: OsNavItem[];
  children: ReactNode;
}

export function OsChrome({ portal, title, accentClass, nav, children }: OsChromeProps) {
  const { me, logout } = useCanonicalAuth();
  const org = useOrg();

  const visibleNav = nav.filter(
    (item) => !item.permission || hasPermission(me, item.permission)
  );

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/90 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href={portal === 'admin' ? '/admin' : portal === 'company' ? '/company' : '/jobseeker'} className="text-sm font-semibold tracking-tight">
            <span className={accentClass}>AskTrabaajo</span>{' '}
            <span className="text-neutral-400">· {title}</span>
          </Link>
          <nav className="flex flex-wrap items-center gap-1 text-sm">
            {visibleNav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded px-2.5 py-1 text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-300 dark:hover:bg-neutral-800 dark:hover:text-white"
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex flex-wrap items-center gap-2 text-sm">
            {portal === 'company' && org.memberships.length > 1 && (
              <select
                value={org.organizationId}
                onChange={(e) => org.selectOrganization(e.target.value)}
                className="rounded border border-neutral-300 bg-white px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900"
                aria-label="Organization"
              >
                {org.memberships.map((m) => (
                  <option key={m.organization_id} value={m.organization_id}>
                    {m.organization_name}
                  </option>
                ))}
              </select>
            )}
            {portal === 'company' && org.membership && (
              <span className="hidden text-xs text-neutral-400 sm:inline">
                {org.membership.role}
              </span>
            )}
            {canAccessJobseekerLink(portal) && (
              <Link className="rounded px-2 py-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800" href="/jobseeker">
                Career
              </Link>
            )}
            {portal !== 'company' && (
              <Link className="rounded px-2 py-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800" href="/company">
                Employer
              </Link>
            )}
            {canAccessPlatform(me) && portal !== 'admin' && (
              <Link className="rounded px-2 py-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800" href="/admin">
                Admin
              </Link>
            )}
            <Link className="rounded px-2 py-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800" href="/id">
              {me?.full_name ?? 'Account'}
            </Link>
            <button
              type="button"
              onClick={() => void logout().then(() => {
                window.location.href = '/login';
              })}
              className="rounded px-2 py-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}

function canAccessJobseekerLink(portal: OsChromeProps['portal']): boolean {
  return portal !== 'jobseeker';
}
