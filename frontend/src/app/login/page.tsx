'use client';

import React, { Suspense, useState } from 'react';
import Logo from '@/components/Logo';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Eye, EyeOff } from 'lucide-react';
import { ApiError } from '@/lib/api/types';
import { loginRedirectPath } from '@/lib/api/portal';
import { useCanonicalAuth } from '@/context/AuthContext';

export default function Login() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 dark:bg-black" />}>
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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-black text-gray-900 dark:text-white p-4 pt-24">
      <div className="w-full max-w-md bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl p-8 shadow-2xl backdrop-blur-sm">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Logo showWordmark={false} variant="gold" />
          </div>
          <h1 className="text-3xl font-bold mb-2">
            Welcome Back to <span className="text-[#D4AF37]">AskTrabaajo</span>
          </h1>
          <p className="text-gray-600 dark:text-white/70">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {!mfaRequired ? (
            <>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  autoComplete="email"
                  className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                  placeholder="you@example.com"
                />
                {errors.email && <p className="text-red-400 text-sm mt-2">{errors.email}</p>}
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    autoComplete="current-password"
                    className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors pr-12"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-white/50 hover:text-gray-700 dark:hover:text-white/80 transition-colors"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
                {errors.password && <p className="text-red-400 text-sm mt-2">{errors.password}</p>}
              </div>
            </>
          ) : (
            <div>
              <label htmlFor="mfa" className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-2">
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
                className="w-full px-4 py-3 bg-white dark:bg-white/10 border border-gray-300 dark:border-white/20 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                placeholder="6-digit code"
              />
              <p className="mt-2 text-sm text-gray-600 dark:text-white/70">
                This account has two-factor authentication enabled.
              </p>
            </div>
          )}

          {!mfaRequired && (
            <div className="flex items-center justify-between">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="w-4 h-4 text-[#D4AF37] bg-white/10 border-white/20 rounded focus:ring-[#D4AF37] focus:ring-2"
                />
                <span className="ml-2 text-sm text-gray-600 dark:text-white/70">Remember me</span>
              </label>
              <Link href="/forgot-password" className="text-sm text-[#D4AF37] hover:text-[#C49F2F] transition-colors">
                Forgot password?
              </Link>
            </div>
          )}

          {errors.general && <p className="text-red-400 text-sm text-center">{errors.general}</p>}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full px-5 py-3 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center"
          >
            {isLoading ? (
              <svg className="animate-spin h-5 w-5 text-black mr-3" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : mfaRequired ? (
              'Verify'
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <p className="text-center text-gray-600 dark:text-white/70 text-sm mt-6">
          Don&apos;t have an account?{' '}
          <Link href="/register" className="text-[#D4AF37] hover:underline">
            Sign Up
          </Link>
        </p>
      </div>
    </div>
  );
}
