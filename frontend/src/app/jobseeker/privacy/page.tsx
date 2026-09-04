"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  ErrorBanner,
  LoadingState,
  PageHeader,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
  labelCls,
} from "@/components/candidate/ui";
import { useCanonicalAuth } from "@/context/AuthContext";
import { api } from "@/lib/api/session";
import { PrivacySettingsOut } from "@/lib/api/types";

const PLAIN: Record<string, string> = {
  profile: "Professional headline and summary",
  experience: "Work history",
  education: "Education",
  skills: "Skills",
  credentials: "Credentials (never shown as verified unless they are)",
  employments: "Employment records",
};

export default function PrivacyPage() {
  const { me, logout } = useCanonicalAuth();
  const [privacy, setPrivacy] = useState<PrivacySettingsOut | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    try {
      setPrivacy(await api.get<PrivacySettingsOut>("/work-id/privacy"));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function save(scope: string, value: string) {
    try {
      await api.put("/work-id/privacy", { settings: { [scope]: value } });
      setNotice("Visibility updated. Employers still cannot see private documents without a grant.");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (error && !privacy) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!privacy) return <LoadingState />;

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Settings"
        title="Privacy & account"
        subtitle="You decide what a company can see. The backend enforces this — hiding a control in the UI does not grant access."
      />
      {error && <ErrorBanner message={error} />}
      {notice && <p className="text-sm text-emerald-400">{notice}</p>}

      <section className={cardCls}>
        <p className={labelCls}>Account</p>
        <p className="mt-2 text-lg font-medium">{me?.full_name}</p>
        <p className="text-sm text-[#9ca3af]">{me?.email}</p>
        <p className="mt-2 text-xs text-[#6b7280]">
          Email {me?.email_verified ? "verified" : "not verified"} · MFA {me?.mfa_enabled ? "on" : "off"}
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link href="/id" className={ghostBtnCls}>
            Security & sessions
          </Link>
          <Link href="/id/work-id" className={ghostBtnCls}>
            Edit Work ID
          </Link>
          <button
            type="button"
            className={btnCls}
            onClick={() => void logout().then(() => { window.location.href = "/login"; })}
          >
            Log out
          </button>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold">What employers can see</h2>
        {privacy.scopes.map((scope) => (
          <div key={scope} className={`${cardCls} flex flex-wrap items-center justify-between gap-3`}>
            <div>
              <p className="font-medium capitalize">{scope.replaceAll("_", " ")}</p>
              <p className="text-xs text-[#9ca3af]">{PLAIN[scope] ?? "Work ID section"}</p>
            </div>
            <select
              className={`${inputCls} w-auto`}
              value={privacy.settings[scope] ?? "private"}
              onChange={(e) => void save(scope, e.target.value)}
            >
              {privacy.allowed_values.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
        ))}
      </section>
    </div>
  );
}
