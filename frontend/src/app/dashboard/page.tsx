'use client';

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { 
  User, 
  Building, 
  Briefcase, 
  Calendar, 
  DollarSign, 
  TrendingUp, 
  Users, 
  FileText,
  Video,
  BarChart3,
  Plus,
  ArrowRight,
  LogOut
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabase';
import { Job, Application, Interview, Notification } from '@/lib/supabase';

export default function Dashboard() {
  const router = useRouter();
  const { user, profile, signOut, loading: authLoading } = useAuth();
  const [stats, setStats] = useState({
    totalJobs: 0,
    applications: 0,
    interviews: 0,
    notifications: 0
  });
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [recentApplications, setRecentApplications] = useState<Application[]>([]);
  const [upcomingInterviews, setUpcomingInterviews] = useState<Interview[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      fetchDashboardData();
    }
  }, [user, authLoading, router]);

  const fetchDashboardData = async () => {
    try {
      // Fetch jobs
      const { data: jobs } = await supabase
        .from('jobs')
        .select('*')
        .eq('status', 'active')
        .order('created_at', { ascending: false })
        .limit(5);

      setRecentJobs(jobs || []);

      // Fetch applications
      const { data: applications } = await supabase
        .from('applications')
        .select(`
          *,
          jobs (
            title,
            company_name
          )
        `)
        .eq('applicant_id', user?.id)
        .order('applied_at', { ascending: false })
        .limit(5);

      setRecentApplications(applications || []);

      // Fetch interviews
      const { data: interviews } = await supabase
        .from('interviews')
        .select(`
          *,
          jobs (
            title
          )
        `)
        .eq('applicant_id', user?.id)
        .gte('scheduled_at', new Date().toISOString())
        .order('scheduled_at', { ascending: true })
        .limit(3);

      setUpcomingInterviews(interviews || []);

      // Fetch notifications
      const { data: notificationsData } = await supabase
        .from('notifications')
        .select('*')
        .eq('user_id', user?.id)
        .eq('read', false)
        .order('created_at', { ascending: false })
        .limit(5);

      setNotifications(notificationsData || []);

      // Calculate stats
      const { count: jobsCount } = await supabase
        .from('jobs')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'active');

      const { count: applicationsCount } = await supabase
        .from('applications')
        .select('*', { count: 'exact', head: true })
        .eq('applicant_id', user?.id);

      const { count: interviewsCount } = await supabase
        .from('interviews')
        .select('*', { count: 'exact', head: true })
        .eq('applicant_id', user?.id)
        .gte('scheduled_at', new Date().toISOString());

      setStats({
        totalJobs: jobsCount || 0,
        applications: applicationsCount || 0,
        interviews: interviewsCount || 0,
        notifications: notificationsData?.length || 0
      });

    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    router.push('/');
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#D4AF37] mx-auto mb-4"></div>
          <p className="text-white">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="bg-black/80 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Link href="/" className="flex items-center space-x-2">
                <Image
                  src="/trabaajo-logo.png"
                  alt="Ask Trabaajo Logo"
                  width={32}
                  height={32}
                  className="h-8 w-auto"
                />
                <span className="text-xl font-bold">AskTrabaajo</span>
              </Link>
            </div>

            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm text-white/70">Welcome back,</p>
                <p className="font-semibold">{profile?.first_name} {profile?.last_name}</p>
              </div>
              <button
                onClick={handleSignOut}
                className="p-2 text-white/70 hover:text-white transition-colors"
              >
                <LogOut size={20} />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Welcome back, <span className="text-[#D4AF37]">{profile?.first_name}</span>
          </h1>
          <p className="text-white/70">
            Here&apos;s what&apos;s happening with your {profile?.role === 'employer' ? 'hiring' : 'job search'} today.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-[#D4AF37] transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Available Jobs</p>
                <p className="text-2xl font-bold text-[#D4AF37]">{stats.totalJobs}</p>
              </div>
              <Briefcase className="h-8 w-8 text-[#D4AF37]" />
            </div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-[#D4AF37] transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">My Applications</p>
                <p className="text-2xl font-bold text-[#D4AF37]">{stats.applications}</p>
              </div>
              <FileText className="h-8 w-8 text-[#D4AF37]" />
            </div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-[#D4AF37] transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Upcoming Interviews</p>
                <p className="text-2xl font-bold text-[#D4AF37]">{stats.interviews}</p>
              </div>
              <Video className="h-8 w-8 text-[#D4AF37]" />
            </div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-[#D4AF37] transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Notifications</p>
                <p className="text-2xl font-bold text-[#D4AF37]">{stats.notifications}</p>
              </div>
              <Users className="h-8 w-8 text-[#D4AF37]" />
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <Link
            href="/jobs"
            className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-[#D4AF37] hover:bg-white/10 transition-all duration-300 group"
          >
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-[#D4AF37]/20 rounded-lg group-hover:bg-[#D4AF37]/30 transition-colors">
                <Briefcase className="h-6 w-6 text-[#D4AF37]" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Browse Jobs</h3>
                <p className="text-sm text-white/70">Find your next opportunity</p>
              </div>
              <ArrowRight className="h-5 w-5 text-white/50 group-hover:text-[#D4AF37] transition-colors ml-auto" />
            </div>
          </Link>

          <Link
            href="/interviews"
            className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-[#D4AF37] hover:bg-white/10 transition-all duration-300 group"
          >
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-[#D4AF37]/20 rounded-lg group-hover:bg-[#D4AF37]/30 transition-colors">
                <Video className="h-6 w-6 text-[#D4AF37]" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Interviews</h3>
                <p className="text-sm text-white/70">Manage your interviews</p>
              </div>
              <ArrowRight className="h-5 w-5 text-white/50 group-hover:text-[#D4AF37] transition-colors ml-auto" />
            </div>
          </Link>

          <Link
            href="/assessment"
            className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-[#D4AF37] hover:bg-white/10 transition-all duration-300 group"
          >
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-[#D4AF37]/20 rounded-lg group-hover:bg-[#D4AF37]/30 transition-colors">
                <BarChart3 className="h-6 w-6 text-[#D4AF37]" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Assessment</h3>
                <p className="text-sm text-white/70">Take skills tests</p>
              </div>
              <ArrowRight className="h-5 w-5 text-white/50 group-hover:text-[#D4AF37] transition-colors ml-auto" />
            </div>
          </Link>
        </div>

        {/* Recent Activity */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Recent Jobs */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Recent Jobs</h3>
              <Link href="/jobs" className="text-[#D4AF37] hover:text-[#C49F2F] text-sm">
                View all
              </Link>
            </div>
            <div className="space-y-3">
              {recentJobs.length > 0 ? (
                recentJobs.map((job) => (
                  <div key={job.id} className="p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                    <h4 className="font-medium text-white">{job.title}</h4>
                    <p className="text-sm text-white/70">{job.location}</p>
                    <p className="text-xs text-white/50">
                      {job.salary_min && job.salary_max 
                        ? `$${job.salary_min.toLocaleString()} - $${job.salary_max.toLocaleString()}`
                        : 'Salary not specified'
                      }
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-white/70 text-center py-4">No recent jobs found</p>
              )}
            </div>
          </div>

          {/* Upcoming Interviews */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Upcoming Interviews</h3>
              <Link href="/interviews" className="text-[#D4AF37] hover:text-[#C49F2F] text-sm">
                View all
              </Link>
            </div>
            <div className="space-y-3">
              {upcomingInterviews.length > 0 ? (
                upcomingInterviews.map((interview) => (
                  <div key={interview.id} className="p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                    <h4 className="font-medium text-white">
                      {interview.jobs?.title || 'Interview'}
                    </h4>
                    <p className="text-sm text-white/70">
                      {new Date(interview.scheduled_at || '').toLocaleDateString()}
                    </p>
                    <p className="text-xs text-white/50 capitalize">
                      {interview.interview_type} • {interview.duration_minutes} minutes
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-white/70 text-center py-4">No upcoming interviews</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
