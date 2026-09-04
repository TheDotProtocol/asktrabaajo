"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { CredentialOut, WorkIdSummary } from "@/lib/api/types";

export default function CredentialsPage() {
  const [work, setWork] = useState<WorkIdSummary | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setWork(await api.get<WorkIdSummary>("/work-id"));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error && !work) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!work) return <LoadingState />;

  const credentials: CredentialOut[] = work.credentials ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Verification"
        title="Credentials"
        subtitle="Status is truthful: verified, pending, unverified, expired, or revoked. Unverified items are never shown as verified."
        actions={
          <Link href="/id/work-id" className={btnCls}>
            Manage on Work ID
          </Link>
        }
      />
      {credentials.length === 0 ? (
        <EmptyState
          title="No credentials yet"
          body="Add a licence, degree, or certificate from your Work ID. Verification is a backend process — this page will not pretend it happened."
          actionHref="/id/work-id"
          actionLabel="Open Work ID"
        />
      ) : (
        <ul className="space-y-3">
          {credentials.map((item) => (
            <li key={item.id} className={cardCls}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{item.name}</p>
                  <p className="text-sm text-[#9ca3af]">{item.issuer ?? "Issuer not listed"} · {item.credential_type}</p>
                  {item.expires_at && (
                    <p className="mt-1 text-xs text-[#6b7280]">Expires {item.expires_at}</p>
                  )}
                </div>
                <StatusPill status={item.status} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
