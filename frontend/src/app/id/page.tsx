"use client";
/**
 * Identity settings — password, email verification, session revoke.
 * Login/register live at /login and /register (canonical session).
 */
import Link from "next/link";
import { useState } from "react";

import { btnCls, cardCls, ghostBtnCls } from "@/components/candidate/ui";
import { api, setSession } from "@/lib/api/session";
import { useCanonicalAuth } from "@/context/AuthContext";

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
        <h1 className="text-2xl font-semibold">Account & security</h1>
        <p className="mt-1 text-sm text-[#9ca3af]">
          Canonical account settings. Sign-in happens at /login. Profile visibility lives under Settings.
        </p>
      </div>

      {notice && <p className="text-sm text-emerald-400">{notice}</p>}
      {error && <p className="text-sm text-red-300">{error}</p>}

      <section className={cardCls}>
        <h2 className="mb-2 font-medium">Account</h2>
        <p className="text-sm">
          {me.full_name} · {me.email}
        </p>
        <p className="text-sm text-[#9ca3af]">
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
            className={ghostBtnCls}
            onClick={doChangePassword}
          >
            Change password
          </button>
          <button
            className={ghostBtnCls}
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
