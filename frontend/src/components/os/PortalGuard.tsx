'use client';

import { useCanonicalAuth } from '@/context/AuthContext';
import {
  canAccessEmployer,
  canAccessGovernance,
  canAccessJobseeker,
} from '@/lib/api/portal';
import { usePathname, useRouter } from 'next/navigation';
import { ReactNode, useEffect } from 'react';

export type PortalAllow = 'authenticated' | 'employer' | 'governance';

export function PortalGuard({
  children,
  allow,
}: {
  children: ReactNode;
  allow: PortalAllow;
}) {
  const { me, loading, error } = useCanonicalAuth();
  const router = useRouter();
  const pathname = usePathname();

  const authorized =
    allow === 'authenticated'
      ? canAccessJobseeker(me)
      : allow === 'employer'
        ? canAccessEmployer(me)
        : canAccessGovernance(me);

  useEffect(() => {
    if (loading) return;
    if (error && !me) return;
    if (!me) {
      const next = pathname && pathname !== '/login' ? `?next=${encodeURIComponent(pathname)}` : '';
      router.replace(`/login${next}`);
    }
  }, [loading, me, error, pathname, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 text-sm text-neutral-500 dark:bg-neutral-950 dark:text-neutral-400">
        Restoring your session…
      </div>
    );
  }

  if (error && !me) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-6 dark:bg-neutral-950">
        <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          <p className="font-medium">Unable to reach AskTrabaajo</p>
          <p className="mt-2">{error}</p>
        </div>
      </div>
    );
  }

  if (!me) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 text-sm text-neutral-500 dark:bg-neutral-950 dark:text-neutral-400">
        Redirecting to sign in…
      </div>
    );
  }

  if (!authorized) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-6 dark:bg-neutral-950">
        <div className="max-w-md rounded-xl border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
          <p className="text-xs uppercase tracking-wide text-neutral-400">403</p>
          <h1 className="mt-1 text-xl font-semibold">You don’t have access to this workspace</h1>
          <p className="mt-2 text-sm text-neutral-500">
            This area is limited by AskTrabaajo permissions. The backend is still the
            authority — this screen only reflects what your account is allowed to open.
          </p>
          <a
            href="/jobseeker"
            className="mt-4 inline-block text-sm font-medium text-amber-600 hover:underline"
          >
            Go to Career OS
          </a>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
