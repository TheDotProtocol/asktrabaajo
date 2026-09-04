import { useEffect, useRef } from "react";

import { btnCls, ghostBtnCls } from "@/components/candidate/ui";
import { confirmButtonLabel } from "@/lib/athena/context";
import { AthenaPendingConfirmation } from "@/lib/api/types";

export function AthenaConfirm({
  pending,
  busy,
  onApprove,
  onCancel,
}: {
  pending: AthenaPendingConfirmation;
  busy: boolean;
  onApprove: () => void;
  onCancel: () => void;
}) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  const label = confirmButtonLabel(pending.tool, pending.action_summary);

  useEffect(() => {
    confirmRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 sm:items-center" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="athena-confirm-title"
        className="w-full max-w-lg rounded-xl border border-[#d4af37]/40 bg-[#0b0c0d] p-6 shadow-2xl"
      >
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#d4af37]">Confirmation required</p>
        <h2 id="athena-confirm-title" className="mt-2 text-xl font-semibold text-white">
          Review this action before it runs
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-[#9ca3af]">
          Athena proposed a high-risk action. The backend will re-check the exact scope, your
          permissions, and a one-time confirmation. Vague approval is not enough.
        </p>
        <dl className="mt-5 space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-[#6b7280]">Action</dt>
            <dd className="text-right text-white">{pending.tool.replaceAll("_", " ")}</dd>
          </div>
          <div>
            <dt className="text-[#6b7280]">Exact intended scope</dt>
            <dd className="mt-1 break-all rounded-md border border-[#23272a] bg-[#111315] p-3 font-mono text-xs text-[#e5e7eb]">
              {pending.action_summary}
            </dd>
          </div>
          {pending.expires_at && (
            <div className="flex justify-between gap-4">
              <dt className="text-[#6b7280]">Expires</dt>
              <dd className="text-white">{new Date(pending.expires_at).toLocaleString()}</dd>
            </div>
          )}
        </dl>
        <div className="mt-6 flex flex-wrap gap-2">
          <button ref={confirmRef} type="button" className={btnCls} disabled={busy} onClick={onApprove}>
            {busy ? "Confirming…" : label}
          </button>
          <button type="button" className={ghostBtnCls} disabled={busy} onClick={onCancel}>
            Cancel this action
          </button>
        </div>
      </div>
    </div>
  );
}
