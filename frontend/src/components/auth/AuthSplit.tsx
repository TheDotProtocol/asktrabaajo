import Link from 'next/link';
import { ReactNode } from 'react';

export function AuthSplit({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="grid min-h-screen bg-[#0b0c0d] lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden px-12 py-14 lg:flex">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_20%,rgba(212,175,55,0.12),transparent_55%)]" />
        <Link href="/" className="relative flex items-center gap-3">
          <span className="size-[18px] rounded-[3px] bg-[#d4af37] shadow-[0_0_8px_#d4af37]" />
          <span className="text-[28px] font-semibold tracking-tight text-white">
            Ask<span className="text-[#d4af37]">Trabaajo</span>
          </span>
        </Link>
        <div className="relative max-w-md">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-[#d4af37]">
            The Operating System for Work
          </p>
          <h2 className="mt-4 text-4xl font-semibold leading-tight text-white">
            One identity. One career record. One control plane.
          </h2>
          <p className="mt-5 text-sm leading-relaxed text-[#9ca3af]">
            Sign in to Candidate OS, Employer OS, or the Super Admin control plane
            with the same AskTrabaajo account.
          </p>
        </div>
        <p className="relative font-mono text-[10px] uppercase tracking-[0.18em] text-[#6b7280]">
          Development
        </p>
      </aside>
      <main className="flex items-center justify-center bg-white px-6 py-12 text-[#111315] sm:px-10">
        <div className="w-full max-w-[420px]">
          <Link href="/" className="mb-8 flex items-center gap-2 lg:hidden">
            <span className="size-3.5 rounded-[3px] bg-[#d4af37]" />
            <span className="text-lg font-semibold">
              Ask<span className="text-[#d4af37]">Trabaajo</span>
            </span>
          </Link>
          <h1 className="text-[32px] font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-[#6b7280]">{subtitle}</p>}
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-8 text-sm text-[#6b7280]">{footer}</div>}
        </div>
      </main>
    </div>
  );
}

export const authInputCls =
  'w-full rounded-lg border border-[#e5e7eb] bg-white px-4 py-3 text-sm text-[#111315] placeholder:text-[#9ca3af] focus:border-[#d4af37] focus:outline-none';

export const authLabelCls = 'mb-2 block text-sm font-medium text-[#374151]';

export const authBtnCls =
  'inline-flex w-full items-center justify-center rounded-lg bg-[#d4af37] px-5 py-3 text-sm font-semibold text-black hover:bg-[#c49f2f] disabled:cursor-not-allowed disabled:opacity-50';
