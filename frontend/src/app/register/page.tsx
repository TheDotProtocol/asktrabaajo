'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { User, Building, Users, Shield, Globe, Check, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

export default function Register() {
  const router = useRouter();
  const { signUp } = useAuth();
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    company: '',
    role: ''
  });
  const [selectedRole, setSelectedRole] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState<{general?: string; email?: string; password?: string; confirmPassword?: string}>({});
  const [isLoading, setIsLoading] = useState(false);

  const roles = [
    {
      id: 'jobseeker',
      title: 'Job Seeker',
      description: 'Looking for opportunities',
      icon: User
    },
    {
      id: 'employer',
      title: 'Employer',
      description: 'Hiring talent',
      icon: Building
    },
    {
      id: 'hr_consultant',
      title: 'HR Consultant',
      description: 'Helping companies hire',
      icon: Users
    },
    {
      id: 'government',
      title: 'Government',
      description: 'Public sector hiring',
      icon: Shield
    },
    {
      id: 'foreign_company',
      title: 'Foreign Company',
      description: 'International operations',
      icon: Globe
    }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});

    if (formData.password !== formData.confirmPassword) {
      setErrors({ confirmPassword: 'Passwords do not match' });
      setIsLoading(false);
      return;
    }

    const { error } = await signUp(formData.email, formData.password, {
      first_name: formData.firstName,
      last_name: formData.lastName,
      role: selectedRole,
      company_name: formData.company
    });
    
    if (error) {
      setErrors({ general: error.message });
    } else {
      router.push('/dashboard');
    }
    
    setIsLoading(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white p-4">
      <div className="w-full max-w-2xl bg-white/5 border border-white/10 rounded-xl p-8 shadow-2xl backdrop-blur-sm">
        <div className="text-center mb-8">
          <Image
            src="/trabaajo-logo.png"
            alt="Ask Trabaajo Logo"
            width={60}
            height={60}
            className="mx-auto mb-4"
          />
          <h1 className="text-3xl font-bold text-white mb-2">
            Join <span className="text-[#D4AF37]">AskTrabaajo</span>
          </h1>
          <p className="text-white/70">Create your account to get started</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Role Selection */}
          <div>
            <label className="block text-sm font-medium text-white/80 mb-4">
              I am a...
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {roles.map((role) => (
                <div
                  key={role.id}
                  className={`p-4 border-2 rounded-xl cursor-pointer transition-all duration-300 ${
                    selectedRole === role.id
                      ? 'border-[#D4AF37] bg-[#D4AF37]/10'
                      : 'border-white/20 hover:border-[#D4AF37]/50 bg-white/5'
                  }`}
                  onClick={() => {
                    setSelectedRole(role.id);
                    setFormData({ ...formData, role: role.id });
                  }}
                >
                  <div className="flex items-center">
                    <div className={`p-2 rounded-lg mr-3 ${
                      selectedRole === role.id ? 'bg-[#D4AF37]/20' : 'bg-white/10'
                    }`}>
                      <role.icon className={`h-5 w-5 ${
                        selectedRole === role.id ? 'text-[#D4AF37]' : 'text-white/70'
                      }`} />
                    </div>
                    <div>
                      <div className="font-medium text-white">{role.title}</div>
                      <div className="text-sm text-white/70">{role.description}</div>
                    </div>
                    {selectedRole === role.id && (
                      <Check className="h-5 w-5 text-[#D4AF37] ml-auto" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Personal Information */}
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="firstName" className="block text-sm font-medium text-white/80 mb-2">
                First Name
              </label>
              <input
                type="text"
                id="firstName"
                name="firstName"
                value={formData.firstName}
                onChange={handleChange}
                required
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                placeholder="John"
              />
            </div>
            <div>
              <label htmlFor="lastName" className="block text-sm font-medium text-white/80 mb-2">
                Last Name
              </label>
              <input
                type="text"
                id="lastName"
                name="lastName"
                value={formData.lastName}
                onChange={handleChange}
                required
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                placeholder="Doe"
              />
            </div>
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-white/80 mb-2">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
              placeholder="you@example.com"
            />
          </div>

          {selectedRole === 'employer' && (
            <div>
              <label htmlFor="company" className="block text-sm font-medium text-white/80 mb-2">
                Company Name
              </label>
              <input
                type="text"
                id="company"
                name="company"
                value={formData.company}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors"
                placeholder="Your Company"
              />
            </div>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-white/80 mb-2">
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
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors pr-12"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/50 hover:text-white/80 transition-colors"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-white/80 mb-2">
              Confirm Password
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:border-[#D4AF37] focus:outline-none transition-colors pr-12"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/50 hover:text-white/80 transition-colors"
              >
                {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="terms"
              required
              className="w-4 h-4 text-[#D4AF37] bg-white/10 border-white/20 rounded focus:ring-[#D4AF37] focus:ring-2"
            />
            <label htmlFor="terms" className="ml-2 text-sm text-white/70">
              I agree to the{' '}
              <Link href="/terms" className="text-[#D4AF37] hover:underline">
                Terms of Service
              </Link>{' '}
              and{' '}
              <Link href="/privacy" className="text-[#D4AF37] hover:underline">
                Privacy Policy
              </Link>
            </label>
          </div>

          {errors.general && <p className="text-red-400 text-sm text-center">{errors.general}</p>}

          <button
            type="submit"
            disabled={isLoading || !selectedRole}
            className="w-full px-5 py-3 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center"
          >
            {isLoading ? (
              <svg className="animate-spin h-5 w-5 text-black mr-3" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        <p className="text-center text-white/70 text-sm mt-6">
          Already have an account?{' '}
          <Link href="/login" className="text-[#D4AF37] hover:underline">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
