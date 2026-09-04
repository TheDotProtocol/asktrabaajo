'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { api } from '@/lib/api/session';
import { ApiError } from '@/lib/api/types';
import { AuthSplit, authBtnCls, authInputCls, authLabelCls } from '@/components/auth/AuthSplit';

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
    <AuthSplit
      title="Reset your password"
      subtitle="If an account exists for this email, AskTrabaajo will send a reset code."
      footer={
        <Link href="/login" className="font-medium text-[#d4af37] hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={onSubmit} className="space-y-5">
        <div>
          <label htmlFor="email" className={authLabelCls}>
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className={authInputCls}
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {notice && <p className="text-sm text-emerald-700">{notice}</p>}
        <button type="submit" disabled={busy} className={authBtnCls}>
          {busy ? 'Sending…' : 'Send reset instructions'}
        </button>
      </form>
    </AuthSplit>
  );
}
