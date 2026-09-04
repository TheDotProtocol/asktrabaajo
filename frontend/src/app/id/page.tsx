"use client";
/**
 * Identity settings — password, email verification, session revoke.
 * Login/register live at /login and /register (canonical session).
 */
import Link from "next/link";
import { useState } from "react";

import { api, setSession } from "@/lib/api/session";
import { useCanonicalAuth } from "@/context/AuthContext";

const btnCls =
  "rounded bg-amber-500 px-4 py-2 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";
const rowCls = "rounded-lg border border-neutral-200 p-4 dark:border-neutral-800";

export default function IdentityPage() {
  const { me, reload, logout } = useCanonicalAuth();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function doChangePassword() {
    setError("");
    const current = window.prompt("Current password");
    const next = window.prompt("New password (8+ chars)");
    if (!current || !next) return;
    try {
      const pair = await api.post<{ access_token: string; refresh_token: string }>(
        "/auth/change-password",
        { current_password: current, new_password: next }
      );
      setSession(pair);
      await reload();
      setNotice("Password changed. All other sessions were revoked.");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function doSendVerification() {
    try {
      await api.post("/auth/verify-email/send", {});
      setNotice("Verification email queued (see backend mail log in dev).");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (!me) {
    return <p className="text-sm text-neutral-500">Loading account…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">My identity</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Canonical account settings. Sign-in happens at /login.
        </p>
      </div>

      {notice && <p className="text-sm text-emerald-700">{notice}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <section className={rowCls}>
        <h2 className="mb-2 font-medium">Account</h2>
        <p className="text-sm">
          {me.full_name} · {me.email}
        </p>
        <p className="text-sm text-neutral-500">
          Email {me.email_verified ? "verified ✓" : "not verified"}{" "}
          {!me.email_verified && (
            <button className="underline" onClick={doSendVerification}>
              send verification email
            </button>
          )}
          {" · "}MFA {me.mfa_enabled ? "enabled" : "disabled"}
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <button
            className="rounded border border-neutral-300 px-2 py-1 dark:border-neutral-700"
            onClick={doChangePassword}
          >
            Change password
          </button>
          <button
            className="rounded border border-neutral-300 px-2 py-1 dark:border-neutral-700"
            onClick={async () => {
              await api.post("/auth/sessions/revoke-all", {});
              setNotice("All sessions revoked — log in again.");
              await logout();
              window.location.href = "/login";
            }}
          >
            Revoke all sessions
          </button>
        </div>
      </section>

      <p className="text-sm">
        Work ID: {me.person ? me.person.headline || "no headline yet" : "—"}
      </p>
      <Link className={btnCls} href="/id/work-id">
        Open Work ID
      </Link>
    </div>
  );
}
