'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ReactNode, useEffect, useState } from 'react';
import {
  Activity,
  BarChart3,
  Bell,
  Briefcase,
  Calendar,
  Cpu,
  Database,
  FileText,
  GitBranch,
  Home,
  LogOut,
  Menu,
  MessageCircle,
  Settings,
  Users,
  X,
} from 'lucide-react';

import { useCanonicalAuth } from '@/context/AuthContext';
import { useOrg } from '@/context/OrgContext';
import { PortalSwitchLinks } from '@/components/os/PortalSwitchLinks';
import { api } from '@/lib/api/session';

type NavItem = {
  href: string;
  label: string;
  icon: typeof Home;
  permission?: string;
  coming?: boolean;
};

const WORKSPACE: NavItem[] = [
  { href: '/company', label: 'Command Center', icon: Home },
  { href: '/company/athena', label: 'Athena HR', icon: Cpu },
  { href: '/company/members', label: 'Workforce', icon: Users, permission: 'members.read' },
  { href: '/company/profile', label: 'Planning', icon: Activity },
  { href: '/company/jobs', label: 'Jobs', icon: Briefcase, permission: 'jobs.view' },
  { href: '/company/candidates', label: 'Talent', icon: Database, permission: 'candidates.search' },
];

const OPERATING: NavItem[] = [
  { href: '/company/pipeline', label: 'Pipeline', icon: GitBranch, permission: 'applications.view' },
  { href: '/company/interviews', label: 'Interviews', icon: Calendar, permission: 'interviews.manage' },
  { href: '/company/offers', label: 'Offers', icon: FileText, permission: 'offers.manage' },
  { href: '/company/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/company/communications', label: 'Messages', icon: MessageCircle, permission: 'communications.read' },
];

const FOOTER: NavItem[] = [
  { href: '/company/notifications', label: 'Notifications', icon: Bell },
  { href: '/employer/billing', label: 'Billing', icon: FileText, permission: 'billing.read' },
  { href: '/company/settings', label: 'Settings', icon: Settings },
];

function isActive(pathname: string, href: string) {
  if (href === '/company') return pathname === '/company';
  return pathname === href || pathname.startsWith(`${href}/`);
}

function allowed(permissions: string[], item: NavItem) {
  if (!item.permission) return true;
  return permissions.includes(item.permission);
}

function NavLink({
  item,
  pathname,
  onClick,
}: {
  item: NavItem;
  pathname: string;
  onClick?: () => void;
}) {
  const active = isActive(pathname, item.href);
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onClick}
      className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
        active
          ? 'border-[#23272a] bg-[#111315] font-semibold text-white'
          : 'border-transparent text-[#9ca3af] hover:bg-white/[0.03] hover:text-white'
      }`}
    >
      <Icon className="size-4 shrink-0" strokeWidth={1.75} />
      <span className="flex-1">{item.label}</span>
      {item.coming && (
        <span className="font-mono text-[9px] uppercase tracking-wider text-[#d4af37]/70">Soon</span>
      )}
    </Link>
  );
}

export function EmployerShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { me, logout } = useCanonicalAuth();
  const { organizationId, membership, memberships, selectOrganization } = useOrg();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const permissions = me?.permissions ?? [];

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ unread: number }>('/jobseeker/notifications/unread-count')
      .then((row) => {
        if (!cancelled) setUnread(row.unread ?? 0);
      })
      .catch(() => {
        if (!cancelled) setUnread(0);
      });
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  const visible = (items: NavItem[]) =>
    items.filter((item) => item.coming || permissions.length === 0 || allowed(permissions, item));

  const sidebar = (
    <aside className="flex h-full w-[240px] shrink-0 flex-col justify-between border-r border-[#23272a] bg-[#0b0c0d] p-5">
      <div className="flex flex-col gap-6 overflow-y-auto">
        <Link href="/company" className="flex items-center gap-2">
          <span className="size-[18px] rounded-[3px] bg-[#d4af37] shadow-[0_0_8px_#d4af37]" />
          <span className="text-lg font-semibold tracking-tight text-white">
            Ask<span className="text-[#d4af37]">Trabaajo</span>
          </span>
        </Link>
        {memberships.length > 0 && (
          <select
            className="w-full rounded-md border border-[#23272a] bg-[#111315] px-2 py-2 text-xs text-white"
            value={organizationId}
            onChange={(e) => selectOrganization(e.target.value)}
            aria-label="Organization"
          >
            {memberships.map((row) => (
              <option key={row.organization_id} value={row.organization_id}>
                {row.organization_name}
              </option>
            ))}
          </select>
        )}
        <nav className="flex flex-col gap-1" aria-label="Workspace">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-[#6b7280]">Workspace</p>
          {visible(WORKSPACE).map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} onClick={() => setOpen(false)} />
          ))}
        </nav>
        <nav className="flex flex-col gap-1" aria-label="HR Operating System">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-[#6b7280]">HR Operating System</p>
          {visible(OPERATING).map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} onClick={() => setOpen(false)} />
          ))}
        </nav>
      </div>
      <div className="flex flex-col gap-3">
        <nav className="flex flex-col gap-1" aria-label="Account">
          {visible(FOOTER).map((item) => (
            <div key={item.href} className="relative">
              <NavLink item={item} pathname={pathname} onClick={() => setOpen(false)} />
              {item.href === '/company/notifications' && unread > 0 && (
                <span className="absolute right-2 top-2 min-w-4 rounded-full bg-[#d4af37] px-1 text-center font-mono text-[10px] text-black">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </div>
          ))}
        </nav>
        <div className="rounded-lg border border-[#23272a] bg-[#111315] p-3">
          <p className="truncate text-sm font-medium text-white">{me?.full_name ?? 'Account'}</p>
          <p className="truncate font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]">
            {membership?.role?.replaceAll('_', ' ') ?? 'No organization'}
          </p>
          <div className="mt-3">
            <PortalSwitchLinks compact />
          </div>
          <button
            type="button"
            onClick={() => void logout().then(() => { window.location.href = '/login'; })}
            className="mt-3 inline-flex items-center gap-1.5 text-xs text-[#9ca3af] hover:text-white"
          >
            <LogOut className="size-3.5" /> Log out
          </button>
        </div>
      </div>
    </aside>
  );

  return (
    <div className="candidate-os min-h-screen bg-[#0b0c0d] text-white">
      <div className="flex min-h-screen">
        <div className="hidden lg:block">{sidebar}</div>
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex items-center justify-between border-b border-[#23272a] bg-[#0b0c0d]/90 px-4 py-3 backdrop-blur lg:hidden">
            <button
              type="button"
              className="rounded-md p-2 text-[#9ca3af]"
              aria-label={open ? 'Close menu' : 'Open menu'}
              onClick={() => setOpen((v) => !v)}
            >
              {open ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
            <span className="text-sm font-semibold">
              Ask<span className="text-[#d4af37]">Trabaajo</span>
            </span>
            <Link href="/company/notifications" className="relative p-2 text-[#9ca3af]">
              <Bell className="size-5" />
              {unread > 0 && <span className="absolute right-1 top-1 size-2 rounded-full bg-[#d4af37]" />}
            </Link>
          </header>
          {open && (
            <div className="fixed inset-0 z-30 lg:hidden">
              <button className="absolute inset-0 bg-black/60" aria-label="Close" onClick={() => setOpen(false)} />
              <div className="relative h-full">{sidebar}</div>
            </div>
          )}
          <main className="min-w-0 flex-1 px-4 py-8 sm:px-8 lg:px-10">{children}</main>
        </div>
      </div>
    </div>
  );
}
