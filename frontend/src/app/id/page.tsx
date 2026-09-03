"use client";
/**
 * Identity proof flow — register / login (incl. MFA step) / me / logout /
 * change password / sessions. Functional validation only; the production UI
 * comes from the Figma design system later.
 */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  api,
  completeMfa,
  fetchMe,
  login,
  logout,
  setSession,
} from "@/lib/api/session";
import { MeResponse } from "@/lib/api/types";

type Mode = "login" | "register" | "mfa";

const inputCls =
  "w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-900";
const btnCls =
  "rounded bg-amber-500 px-4 py-2 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";
const rowCls = "rounded-lg border border-neutral-200 p-4 dark:border-neutral-800";

export default function IdentityPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [mode, setMode] = useState<Mode>("login");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [mfaCode, setMfaCode] = useState("");

  const reload = useCallback(async () => {
    setMe(await fetchMe());
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function doRegister() {
    setError("");
    try {
      const pair = await api.post<{ access_token: string; refresh_token: string }>(
        "/auth/register",
        { email, password, full_name: fullName || "Test Person" }
      );
      setSession(pair);
      await reload();
      setNotice("Account created.");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function doLogin() {
    setError("");
    try {
      const outcome = await login(email, password);
      if (outcome.mfaRequired) {
        setMode("mfa");
        return;
      }
      await reload();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function doMfa() {
    setError("");
    try {
      const outcome = await completeMfa(mfaCode);
      if (outcome.ok) {
        setMode("login");
        await reload();
      }
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

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

  async function doLogout() {
    await logout();
    setMe(null);
    setMode("login");
  }

  if (!me) {
    return (
      <main className="mx-auto max-w-md px-6 py-12">
        <h1 className="text-2xl font-semibold">AskTrabaajo Identity</h1>
        <p className="mb-6 text-sm text-neutral-500">
          Canonical identity proof flow (<code>/api/v1/auth</code>).
        </p>

        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        {mode !== "mfa" ? (
          <div className="space-y-3">
            <input
              className={inputCls}
              placeholder="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              className={inputCls}
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {mode === "register" && (
              <input
                className={inputCls}
                placeholder="Full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            )}
            <div className="flex gap-2">
              <button
                className={btnCls}
                disabled={!email || password.length < 8}
                onClick={mode === "login" ? doLogin : doRegister}
              >
                {mode === "login" ? "Log in" : "Create account"}
              </button>
              <button
                className="text-sm text-neutral-500 underline"
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError("");
                }}
              >
                {mode === "login" ? "Register instead" : "Log in instead"}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm">
              Two-factor authentication enabled — enter your authenticator code.
            </p>
            <input
              className={inputCls}
              placeholder="6-digit code"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
            />
            <button
              className={btnCls}
              disabled={mfaCode.length !== 6}
              onClick={doMfa}
            >
              Verify
            </button>
          </div>
        )}
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">My identity</h1>
        <button className="text-sm text-red-600" onClick={doLogout}>
          Log out
        </button>
      </div>

      {notice && <p className="mb-3 text-sm text-emerald-700">{notice}</p>}
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <section className={`${rowCls} mb-4`}>
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
              doLogout();
            }}
          >
            Revoke all sessions
          </button>
        </div>
      </section>

      <p className="mb-2 text-sm">
        Work ID: {me.person ? me.person.headline || "no headline yet" : "—"}
      </p>
      <Link className={btnCls} href="/id/work-id">
        Open Work ID
      </Link>
    </main>
  );
}
