"use client";
/**
 * Platform audit review (Phase 10 proof).
 *
 * Search/filter the canonical audit log by actor, organization, action,
 * resource, result, request id and time. Payloads are sanitized server-side:
 * passwords, tokens, secrets and message bodies never reach this screen.
 */
import { useCallback, useEffect, useState } from "react";

import { PageHeader, cardCls, ghostBtnCls, inputCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { GovernanceAuditPage, GovernanceAuditRow } from "@/lib/api/types";

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
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [result, setResult] = useState("");
  const [requestId, setRequestId] = useState("");
  const [fromTs, setFromTs] = useState("");
  const [toTs, setToTs] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "50" });
    if (actionPrefix) params.set("action_prefix", actionPrefix);
    if (action) params.set("action", action);
    if (actor) params.set("actor", actor);
    if (organizationId) params.set("organization_id", organizationId);
    if (resourceType) params.set("resource_type", resourceType);
    if (resourceId) params.set("resource_id", resourceId);
    if (result) params.set("result", result);
    if (requestId) params.set("request_id", requestId);
    if (fromTs) params.set("from_ts", new Date(fromTs).toISOString());
    if (toTs) params.set("to_ts", new Date(toTs).toISOString());
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
  }, [page, actionPrefix, action, actor, organizationId, resourceType, resourceId, result, requestId, fromTs, toTs]);

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
      placeholder: "e.g. governance. | enforcement. | appeal.",
    },
    { label: "Exact action", value: action, set: setAction, placeholder: "e.g. appeal.decided" },
    { label: "Actor UUID", value: actor, set: setActor, placeholder: "…" },
    { label: "Organization UUID", value: organizationId, set: setOrganizationId, placeholder: "…" },
    {
      label: "Resource type",
      value: resourceType,
      set: setResourceType,
      placeholder: "case | enforcement_action | appeal | user",
    },
    { label: "Resource / case / enforcement ID", value: resourceId, set: setResourceId, placeholder: "…" },
    {
      label: "Result",
      value: result,
      set: setResult,
      placeholder: "success | failure",
    },
    { label: "Request ID", value: requestId, set: setRequestId, placeholder: "…" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Audit"
        title="Metadata-only review"
        subtitle="Who did what, to what, when. Passwords, credentials, message bodies, and private documents never appear. Severity is not a first-class audit filter — use action prefix and result instead."
      />

      <div className={`${cardCls} space-y-3`}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {fields.map((field) => (
            <label key={field.label} className="block">
              <span className="text-xs font-medium text-[#9ca3af]">
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
          <label className="block">
            <span className="text-xs font-medium text-[#9ca3af]">From</span>
            <input
              type="datetime-local"
              value={fromTs}
              onChange={(e) => {
                setFromTs(e.target.value);
                setPage(1);
              }}
              className={`${inputCls} mt-1 w-full`}
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-[#9ca3af]">To</span>
            <input
              type="datetime-local"
              value={toTs}
              onChange={(e) => {
                setToTs(e.target.value);
                setPage(1);
              }}
              className={`${inputCls} mt-1 w-full`}
            />
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setActionPrefix("");
              setAction("");
              setActor("");
              setOrganizationId("");
              setResourceType("");
              setResourceId("");
              setResult("");
              setRequestId("");
              setFromTs("");
              setToTs("");
              setPage(1);
            }}
            className={ghostBtnCls}
          >
            Clear filters
          </button>
          <span className="ml-auto text-xs text-[#9ca3af]">
            {pageData ? `${pageData.total} event${pageData.total === 1 ? "" : "s"}` : "…"}
          </span>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
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
