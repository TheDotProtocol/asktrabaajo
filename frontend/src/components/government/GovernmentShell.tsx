"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useState } from "react";
import {
  BarChart3,
  Briefcase,
  Building2,
  Globe2,
  Home,
  LogOut,
  Map,
  Menu,
  Settings,
  Sparkles,
  Target,
  X,
} from "lucide-react";

import { PortalSwitchLinks } from "@/components/os/PortalSwitchLinks";
import { useCanonicalAuth } from "@/context/AuthContext";

type NavItem = { href: string; label: string; icon: typeof Home; future?: boolean };

const PRIMARY: NavItem[] = [
  { href: "/government", label: "Command Center", icon: Home },
  { href: "/government/workforce", label: "Workforce", icon: BarChart3 },
  { href: "/government/skills", label: "Skills", icon: Target },
  { href: "/government/geography", label: "Geography", icon: Map },
  { href: "/government/industries", label: "Industry", icon: Globe2 },
  { href: "/government/opportunities", label: "Opportunities", icon: Briefcase },
  { href: "/government/companies", label: "Companies", icon: Building2 },
  { href: "/government/reports", label: "Reports", icon: BarChart3 },
  { href: "/government/athena", label: "Athena", icon: Sparkles },
];

const SECONDARY: NavItem[] = [
  { href: "/government/investment", label: "Investment", icon: Target, future: true },
  { href: "/government/settings", label: "Settings", icon: Settings },
];

function isActive(pathname: string, href: string) {
  if (href === "/government") return pathname === "/government";
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
          ? "border-[#23272a] bg-[#111315] font-semibold text-white"
          : "border-transparent text-[#9ca3af] hover:bg-white/[0.03] hover:text-white"
      }`}
    >
      <Icon className="size-4 shrink-0" strokeWidth={1.75} />
      <span className="flex-1">{item.label}</span>
      {item.future && (
        <span className="font-mono text-[9px] uppercase tracking-wider text-[#d4af37]/70">Future</span>
      )}
    </Link>
  );
}

export function GovernmentShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { logout } = useCanonicalAuth();
  const [open, setOpen] = useState(false);

  return (
    <div className="candidate-os min-h-screen bg-[#0b0c0d] text-white">
      <div className="flex min-h-screen">
        <aside className="hidden w-[240px] shrink-0 border-r border-[#23272a] bg-[#0b0c0d] lg:flex lg:flex-col">
          <div className="border-b border-[#23272a] px-5 py-5">
            <Link href="/government" className="text-lg font-semibold tracking-tight">
              Ask<span className="text-[#d4af37]">Trabaajo</span>
            </Link>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-[#9ca3af]">
              Government OS
            </p>
          </div>
          <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
            {PRIMARY.map((item) => (
              <NavLink key={item.href} item={item} pathname={pathname} />
            ))}
            <div className="pt-4">
              {SECONDARY.map((item) => (
                <NavLink key={item.href} item={item} pathname={pathname} />
              ))}
            </div>
          </nav>
          <div className="border-t border-[#23272a] px-3 py-4">
            <PortalSwitchLinks compact />
            <button
              type="button"
              onClick={() => logout()}
              className="mt-3 flex w-full items-center gap-2 px-3 py-2 text-sm text-[#9ca3af] hover:text-white"
            >
              <LogOut className="size-4" />
              Sign out
            </button>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="flex items-center justify-between border-b border-[#23272a] px-4 py-4 lg:hidden">
            <Link href="/government" className="text-lg font-semibold">
              Ask<span className="text-[#d4af37]">Trabaajo</span>
            </Link>
            <button type="button" aria-label="Open menu" onClick={() => setOpen(true)}>
              <Menu className="size-6" />
            </button>
          </header>
          {open && (
            <div className="fixed inset-0 z-40 bg-black/70 lg:hidden">
              <div className="h-full w-[280px] overflow-y-auto bg-[#0b0c0d] p-4">
                <button type="button" aria-label="Close menu" className="mb-4" onClick={() => setOpen(false)}>
                  <X className="size-6" />
                </button>
                {PRIMARY.concat(SECONDARY).map((item) => (
                  <NavLink key={item.href} item={item} pathname={pathname} onClick={() => setOpen(false)} />
                ))}
              </div>
            </div>
          )}
          <div className="border-b border-[#23272a] bg-[#111315] px-4 py-2 text-center font-mono text-[10px] uppercase tracking-[0.16em] text-[#d4af37] sm:px-8">
            Privacy-protected aggregate data · Individual records are not exposed
          </div>
          <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
