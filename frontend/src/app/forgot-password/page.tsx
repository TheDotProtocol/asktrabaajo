'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { api } from '@/lib/api/session';
import { ApiError } from '@/lib/api/types';
import Logo from '@/components/Logo';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await api.post<{ message: string }>('/auth/forgot-password', { email });
      setNotice(result.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to request a reset.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4 pt-24 dark:bg-black">
      <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-8 dark:border-white/10 dark:bg-white/5">
        <div className="mb-6 flex justify-center">
          <Logo showWordmark={false} variant="gold" />
        </div>
        <h1 className="text-2xl font-semibold">Reset your password</h1>
        <p className="mt-2 text-sm text-neutral-500">
          If an account exists for this email, AskTrabaajo will send a reset code.
        </p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-lg border border-gray-300 px-4 py-3 dark:border-white/20 dark:bg-white/10"
          />
          {error && <p className="text-sm text-red-500">{error}</p>}
          {notice && <p className="text-sm text-emerald-600">{notice}</p>}
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-[#D4AF37] px-4 py-3 font-semibold text-black disabled:opacity-50"
          >
            {busy ? 'Sending…' : 'Send reset instructions'}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-neutral-500">
          <Link href="/login" className="text-[#D4AF37] hover:underline">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
