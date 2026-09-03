"use client";
/**
 * Platform audit review (Phase 10 proof).
 *
 * Search/filter the canonical audit log by actor, organization, action,
 * resource, result, request id and time. Payloads are sanitized server-side:
 * passwords, tokens, secrets and message bodies never reach this screen.
 */
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import { GovernanceAuditPage, GovernanceAuditRow } from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const inputCls =
  "rounded border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900";
const chipCls =
  "rounded px-2 py-1 text-xs font-medium bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300";

function fmt(ts: string | null): string {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

export default function AuditReviewPage() {
  const [pageData, setPageData] = useState<GovernanceAuditPage | null>(null);
  const [actionPrefix, setActionPrefix] = useState("");
  const [actor, setActor] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [result, setResult] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "50" });
    if (actionPrefix) params.set("action_prefix", actionPrefix);
    if (actor) params.set("actor", actor);
    if (resourceType) params.set("resource_type", resourceType);
    if (resourceId) params.set("resource_id", resourceId);
    if (result) params.set("result", result);
    try {
      const data = await api.get<GovernanceAuditPage>(
        `/governance/audit?${params.toString()}`
      );
      setPageData(data);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [page, actionPrefix, actor, resourceType, resourceId, result]);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        Your account does not hold the platform audit review permission.
      </div>
    );
  }

  const fields: Array<{
    label: string;
    value: string;
    set: (v: string) => void;
    placeholder: string;
    className?: string;
  }> = [
    {
      label: "Action prefix",
      value: actionPrefix,
      set: setActionPrefix,
      placeholder: "e.g. governance.",
    },
    { label: "Actor UUID", value: actor, set: setActor, placeholder: "…" },
    {
      label: "Resource type",
      value: resourceType,
      set: setResourceType,
      placeholder: "e.g. offer",
    },
    { label: "Resource ID", value: resourceId, set: setResourceId, placeholder: "…" },
    {
      label: "Result",
      value: result,
      set: setResult,
      placeholder: "success | failure",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Audit review</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Who did what, to what, when — with context and result. Secrets and
          message bodies are never shown.
        </p>
      </div>

      <div className={`${cardCls} space-y-3`}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {fields.map((field) => (
            <label key={field.label} className="block">
              <span className="text-xs font-medium text-neutral-500">
                {field.label}
              </span>
              <input
                value={field.value}
                onChange={(e) => {
                  field.set(e.target.value);
                  setPage(1);
                }}
                placeholder={field.placeholder}
                className={`${inputCls} mt-1 w-full`}
              />
            </label>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => {
              setActionPrefix("");
              setActor("");
              setResourceType("");
              setResourceId("");
              setResult("");
              setPage(1);
            }}
            className={chipCls}
          >
            Clear filters
          </button>
          <span className="ml-auto text-xs text-neutral-500">
            {pageData ? `${pageData.total} event${pageData.total === 1 ? "" : "s"}` : "…"}
          </span>
        </div>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>

      <div className={`${cardCls} space-y-2`}>
        {(pageData?.items ?? []).length === 0 && !error && (
          <p className="text-sm text-neutral-500">No audit events match.</p>
        )}
        {pageData?.items.map((row: GovernanceAuditRow) => (
          <div
            key={row.id}
            className="rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
          >
            <div className="flex flex-wrap items-center gap-2">
              <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs dark:bg-neutral-800">
                {row.action}
              </code>
              <span className="text-xs text-neutral-500">
                {row.actor_name ?? row.actor_id?.slice(0, 8) ?? "system"}
              </span>
              <span
                className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                  row.result === "failure"
                    ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                    : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
                }`}
              >
                {row.result}
              </span>
              <span className="ml-auto text-xs text-neutral-400">
                {fmt(row.created_at)}
              </span>
            </div>
            <p className="mt-1 text-xs text-neutral-500">
              {row.resource_type ? `${row.resource_type} ` : ""}
              {row.resource_id ? (
                <code className="rounded bg-neutral-100 px-1 py-0.5 text-[10px] dark:bg-neutral-800">
                  {row.resource_id.slice(0, 24)}
                </code>
              ) : null}
              {row.organization_id ? ` · org ${row.organization_id.slice(0, 8)}…` : ""}
              {row.request_id ? ` · req ${row.request_id.slice(0, 12)}` : ""}
            </p>
            {row.payload && Object.keys(row.payload).length > 0 && (
              <p className="mt-1 break-all text-[11px] text-neutral-400">
                {JSON.stringify(row.payload)}
              </p>
            )}
          </div>
        ))}
      </div>

      {pageData && pageData.total > pageData.page_size && (
        <div className="flex items-center justify-between text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded border border-neutral-300 px-3 py-1.5 disabled:opacity-40 dark:border-neutral-700"
          >
            Previous
          </button>
          <span className="text-xs text-neutral-500">
            Page {pageData.page} of{" "}
            {Math.max(1, Math.ceil(pageData.total / pageData.page_size))}
          </span>
          <button
            disabled={page * pageData.page_size >= pageData.total}
            onClick={() => setPage((p) => p + 1)}
            className="rounded border border-neutral-300 px-3 py-1.5 disabled:opacity-40 dark:border-neutral-700"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
