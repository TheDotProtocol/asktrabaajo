'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ReactNode, useEffect, useState } from 'react';
import {
  ArrowUpRight,
  BarChart3,
  Bell,
  Briefcase,
  Calendar,
  FileStack,
  FileText,
  Gift,
  Home,
  LogOut,
  Menu,
  MessageCircle,
  Settings,
  ShieldCheck,
  Sparkles,
  UserRound,
  X,
} from 'lucide-react';

import { useCanonicalAuth } from '@/context/AuthContext';
import { api } from '@/lib/api/session';

type NavItem = {
  href: string;
  label: string;
  icon: typeof Home;
  coming?: boolean;
};

const PRIMARY: NavItem[] = [
  { href: '/jobseeker', label: 'Home', icon: Home },
  { href: '/id/work-id', label: 'Work ID', icon: FileText },
  { href: '/jobseeker/athena', label: 'Athena', icon: Sparkles, coming: true },
  { href: '/jobseeker/work-dna', label: 'Work DNA', icon: UserRound },
  { href: '/jobseeker/career', label: 'Career', icon: BarChart3 },
  { href: '/jobseeker/opportunities', label: 'Opportunities', icon: Briefcase },
  { href: '/jobseeker/applications', label: 'Applications', icon: ArrowUpRight },
  { href: '/jobseeker/interviews', label: 'Interviews', icon: Calendar },
  { href: '/jobseeker/offers', label: 'Offers', icon: Gift },
  { href: '/jobseeker/credentials', label: 'Credentials', icon: ShieldCheck },
];

const SECONDARY: NavItem[] = [
  { href: '/jobseeker/documents', label: 'Documents', icon: FileStack },
  { href: '/jobseeker/notifications', label: 'Notifications', icon: Bell },
  { href: '/jobseeker/communications', label: 'Messages', icon: MessageCircle },
  { href: '/jobseeker/privacy', label: 'Settings', icon: Settings },
];

function isActive(pathname: string, href: string) {
  if (href === '/jobseeker') return pathname === '/jobseeker';
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLink({ item, pathname, onClick }: { item: NavItem; pathname: string; onClick?: () => void }) {
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

export function CandidateShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { me, logout } = useCanonicalAuth();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);

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

  const firstName = (me?.full_name || 'there').split(' ')[0];
  const headline = me?.person?.headline ?? 'Build your Work ID';

  const sidebar = (
    <aside className="flex h-full w-[240px] shrink-0 flex-col justify-between border-r border-[#23272a] bg-[#0b0c0d] p-5">
      <div className="flex flex-col gap-8">
        <Link href="/jobseeker" className="flex items-center gap-2">
          <span className="size-[18px] rounded-[3px] bg-[#d4af37] shadow-[0_0_8px_#d4af37]" />
          <span className="text-lg font-semibold tracking-tight text-white">
            Ask<span className="text-[#d4af37]">Trabaajo</span>
          </span>
        </Link>
        <nav className="flex flex-col gap-1 overflow-y-auto" aria-label="Candidate">
          {PRIMARY.map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} onClick={() => setOpen(false)} />
          ))}
        </nav>
      </div>
      <div className="flex flex-col gap-4">
        <nav className="flex flex-col gap-1.5" aria-label="Account">
          {SECONDARY.map((item) => (
            <div key={item.href} className="relative">
              <NavLink item={item} pathname={pathname} onClick={() => setOpen(false)} />
              {item.href === '/jobseeker/notifications' && unread > 0 && (
                <span className="absolute right-2 top-2 min-w-4 rounded-full bg-[#d4af37] px-1 text-center font-mono text-[10px] text-black">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </div>
          ))}
        </nav>
        <div className="rounded-lg border border-[#23272a] bg-[#111315] p-3">
          <p className="truncate text-sm font-medium text-white">{me?.full_name ?? 'Account'}</p>
          <p className="truncate font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]">{headline}</p>
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
            <Link href="/jobseeker/notifications" className="relative p-2 text-[#9ca3af]">
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
          <main className="min-w-0 flex-1 px-4 py-8 sm:px-8 lg:px-10">
            <p className="sr-only">Signed in as {firstName}</p>
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
