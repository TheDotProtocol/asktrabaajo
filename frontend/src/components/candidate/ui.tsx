import Link from 'next/link';
import { ReactNode } from 'react';

export const cardCls =
  'rounded-xl border border-[#23272a] bg-[#111315] p-5';
export const labelCls = 'font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]';
export const btnCls =
  'inline-flex items-center justify-center rounded-md bg-[#d4af37] px-4 py-2 text-sm font-semibold text-black hover:bg-[#e4c35a] disabled:opacity-50';
export const ghostBtnCls =
  'inline-flex items-center justify-center rounded-md border border-[#23272a] px-4 py-2 text-sm text-[#e5e7eb] hover:border-[#d4af37]/50 hover:text-white disabled:opacity-50';
export const inputCls =
  'w-full rounded-md border border-[#23272a] bg-[#0b0c0d] px-3 py-2 text-sm text-white placeholder:text-[#6b7280] focus:border-[#d4af37] focus:outline-none';

export function PageHeader({
  kicker,
  title,
  subtitle,
  actions,
}: {
  kicker?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        {kicker && <p className={labelCls}>{kicker}</p>}
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#9ca3af]">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  actionHref,
  actionLabel,
}: {
  title: string;
  body: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <div className={`${cardCls} text-center`}>
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-[#9ca3af]">{body}</p>
      {actionHref && actionLabel && (
        <Link href={actionHref} className={`${btnCls} mt-5`}>
          {actionLabel}
        </Link>
      )}
    </div>
  );
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return <div className="py-20 text-center text-sm text-[#9ca3af]">{label}</div>;
}

export function ErrorBanner({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-200">
      {message}
      {onRetry && (
        <button type="button" onClick={onRetry} className="ml-3 underline">
          Retry
        </button>
      )}
    </div>
  );
}

export function StatusPill({
  status,
  tone,
}: {
  status: string;
  tone?: 'gold' | 'green' | 'red' | 'muted';
}) {
  const resolved =
    tone ??
    (['verified', 'accepted', 'completed', 'active'].some((s) => status.toLowerCase().includes(s))
      ? 'green'
      : ['pending', 'review', 'interview'].some((s) => status.toLowerCase().includes(s))
        ? 'gold'
        : ['expired', 'revoked', 'declined', 'withdrawn'].some((s) => status.toLowerCase().includes(s))
          ? 'red'
          : 'muted');
  const cls = {
    gold: 'border-[#d4af37]/40 bg-[#d4af37]/10 text-[#d4af37]',
    green: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
    red: 'border-red-500/30 bg-red-500/10 text-red-300',
    muted: 'border-[#23272a] bg-[#0b0c0d] text-[#9ca3af]',
  }[resolved];
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${cls}`}>
      {status.replaceAll('_', ' ')}
    </span>
  );
}
