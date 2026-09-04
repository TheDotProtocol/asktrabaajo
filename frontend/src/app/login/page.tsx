'use client';

import React, { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Eye, EyeOff } from 'lucide-react';
import { ApiError } from '@/lib/api/types';
import { loginRedirectPath } from '@/lib/api/portal';
import { useCanonicalAuth } from '@/context/AuthContext';
import { AuthSplit, authBtnCls, authInputCls, authLabelCls } from '@/components/auth/AuthSplit';

export default function Login() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0b0c0d]" />}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get('next');
  const { login, verifyMfa, consumeIntent } = useCanonicalAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [mfaCode, setMfaCode] = useState('');
  const [mfaRequired, setMfaRequired] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; general?: string }>({});
  const [isLoading, setIsLoading] = useState(false);

  const goAuthenticated = (me: Parameters<typeof loginRedirectPath>[0]) => {
    const intent = consumeIntent();
    router.push(loginRedirectPath(me, next, intent));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});

    try {
      if (mfaRequired) {
        const outcome = await verifyMfa(mfaCode.trim());
        if (!outcome.ok) {
          setErrors({ general: outcome.message ?? 'Invalid authentication code.' });
        } else {
          goAuthenticated(outcome.me);
        }
        return;
      }

      const outcome = await login(formData.email, formData.password);
      if (outcome.mfaRequired) {
        setMfaRequired(true);
        return;
      }
      if (!outcome.ok) {
        setErrors({ general: outcome.message ?? 'Invalid email or password.' });
        return;
      }
      goAuthenticated(outcome.me);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'Unable to sign in. Please try again.';
      setErrors({ general: message });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthSplit
      title="Welcome back"
      subtitle="Sign in to your AskTrabaajo account."
      footer={
        <p>
          Don&apos;t have an account?{' '}
          <Link href="/register" className="font-medium text-[#d4af37] hover:underline">
            Sign up
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {!mfaRequired ? (
          <>
            <div>
              <label htmlFor="email" className={authLabelCls}>
                Email
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                autoComplete="email"
                className={authInputCls}
                placeholder="you@example.com"
              />
              {errors.email && <p className="mt-2 text-sm text-red-600">{errors.email}</p>}
            </div>
            <div>
              <label htmlFor="password" className={authLabelCls}>
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  autoComplete="current-password"
                  className={`${authInputCls} pr-12`}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9ca3af] hover:text-[#111315]"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {errors.password && <p className="mt-2 text-sm text-red-600">{errors.password}</p>}
            </div>
          </>
        ) : (
          <div>
            <label htmlFor="mfa" className={authLabelCls}>
              Authentication code
            </label>
            <input
              id="mfa"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              required
              maxLength={6}
              className={authInputCls}
              placeholder="6-digit code"
            />
            <p className="mt-2 text-sm text-[#6b7280]">
              This account has two-factor authentication enabled.
            </p>
          </div>
        )}

        {!mfaRequired && (
          <div className="flex items-center justify-between">
            <label className="flex items-center text-sm text-[#6b7280]">
              <input type="checkbox" className="mr-2 size-4 rounded border-[#d1d5db] text-[#d4af37]" />
              Remember me
            </label>
            <Link href="/forgot-password" className="text-sm font-medium text-[#d4af37] hover:underline">
              Forgot password?
            </Link>
          </div>
        )}

        {errors.general && <p className="text-center text-sm text-red-600">{errors.general}</p>}

        <button type="submit" disabled={isLoading} className={authBtnCls}>
          {isLoading ? 'Signing in…' : mfaRequired ? 'Verify' : 'Sign in'}
        </button>
      </form>
    </AuthSplit>
  );
}
