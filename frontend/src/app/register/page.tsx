'use client';

import React, { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Eye, EyeOff } from 'lucide-react';
import { ApiError } from '@/lib/api/types';
import { loginRedirectPath } from '@/lib/api/portal';
import { useCanonicalAuth } from '@/context/AuthContext';
import type { PostAuthIntent } from '@/lib/api/session';
import { AuthSplit, authBtnCls, authInputCls, authLabelCls } from '@/components/auth/AuthSplit';

function intentFromQuery(raw: string | null): PostAuthIntent {
  if (raw === 'employer' || raw === 'company' || raw === 'recruiter') return 'employer';
  return 'jobseeker';
}

export default function Register() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0b0c0d]" />}>
      <RegisterForm />
    </Suspense>
  );
}

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register, consumeIntent } = useCanonicalAuth();
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [intent, setIntent] = useState<PostAuthIntent>(() =>
    intentFromQuery(searchParams.get('intent'))
  );
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState<{
    general?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
  }>({});
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});

    if (formData.password.length < 8) {
      setErrors({ password: 'Password must be at least 8 characters.' });
      setIsLoading(false);
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setErrors({ confirmPassword: 'Passwords do not match' });
      setIsLoading(false);
      return;
    }

    const fullName = `${formData.firstName} ${formData.lastName}`.trim();
    if (!fullName) {
      setErrors({ general: 'Please enter your name.' });
      setIsLoading(false);
      return;
    }

    try {
      const outcome = await register(formData.email, formData.password, fullName, intent);
      if (!outcome.ok) {
        setErrors({ general: outcome.message ?? 'Unable to create the account.' });
        return;
      }
      consumeIntent();
      router.push(loginRedirectPath(outcome.me, null, intent));
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'Unable to create the account.';
      setErrors({ general: message });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthSplit
      title="Create your account"
      subtitle="Join AskTrabaajo as a candidate or start an employer workspace after sign-in."
      footer={
        <p>
          Already have an account?{' '}
          <Link href="/login" className="font-medium text-[#d4af37] hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <p className={authLabelCls}>I am joining as</p>
          <div className="grid grid-cols-2 gap-2">
            {(
              [
                ['jobseeker', 'Jobseeker'],
                ['employer', 'Employer'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setIntent(id)}
                className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                  intent === id
                    ? 'border-[#d4af37] bg-[#d4af37]/10 text-[#111315]'
                    : 'border-[#e5e7eb] text-[#6b7280]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs text-[#9ca3af]">
            Government and platform roles are assigned by an administrator — they are not
            self-selected.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="firstName" className={authLabelCls}>
              First name
            </label>
            <input
              type="text"
              id="firstName"
              name="firstName"
              value={formData.firstName}
              onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
              required
              className={authInputCls}
              placeholder="John"
            />
          </div>
          <div>
            <label htmlFor="lastName" className={authLabelCls}>
              Last name
            </label>
            <input
              type="text"
              id="lastName"
              name="lastName"
              value={formData.lastName}
              onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
              required
              className={authInputCls}
              placeholder="Doe"
            />
          </div>
        </div>

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
              minLength={8}
              autoComplete="new-password"
              className={`${authInputCls} pr-12`}
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9ca3af]"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {errors.password && <p className="mt-2 text-sm text-red-600">{errors.password}</p>}
        </div>

        <div>
          <label htmlFor="confirmPassword" className={authLabelCls}>
            Confirm password
          </label>
          <div className="relative">
            <input
              type={showConfirmPassword ? 'text' : 'password'}
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              required
              autoComplete="new-password"
              className={`${authInputCls} pr-12`}
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9ca3af]"
              aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
            >
              {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {errors.confirmPassword && (
            <p className="mt-2 text-sm text-red-600">{errors.confirmPassword}</p>
          )}
        </div>

        <label className="flex items-start gap-2 text-sm text-[#6b7280]">
          <input type="checkbox" required className="mt-0.5 size-4 rounded border-[#d1d5db]" />
          <span>
            I agree to the{' '}
            <Link href="/terms" className="text-[#d4af37] hover:underline">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link href="/privacy" className="text-[#d4af37] hover:underline">
              Privacy Policy
            </Link>
          </span>
        </label>

        {errors.general && <p className="text-center text-sm text-red-600">{errors.general}</p>}

        <button type="submit" disabled={isLoading} className={authBtnCls}>
          {isLoading ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthSplit>
  );
}
