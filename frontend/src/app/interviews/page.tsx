'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft,
  Plus,
  Video,
  Clock,
  User,
  Building,
  Calendar,
  CheckCircle,
  XCircle,
  Play,
  Eye,
  ArrowRight,
  Search
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabase';
import { Interview } from '@/lib/supabase';

export default function Interviews() {
  const router = useRouter();
  const { user, profile, loading: authLoading } = useAuth();
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const fetchInterviews = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('interviews')
        .select(`
          *,
          jobs (
            title,
            employer_id,
            profiles!jobs_employer_id_fkey (
              company_name,
              first_name,
              last_name
            )
          )
        `)
        .eq(profile?.role === 'employer' ? 'employer_id' : 'applicant_id', user?.id)
        .order('scheduled_at', { ascending: false });

      if (error) throw error;
      setInterviews(data || []);
    } catch (error) {
      console.error('Error fetching interviews:', error);
    } finally {
      setIsLoading(false);
    }
  }, [user, profile]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      fetchInterviews();
    }
  }, [user, authLoading, router, fetchInterviews]);

  const filteredInterviews = interviews.filter(interview => {
    const matchesSearch = true; // Simplified for now
    const matchesStatus = statusFilter === 'all' || interview.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'scheduled': return 'text-blue-400 bg-blue-400/20';
      case 'in-progress': return 'text-yellow-400 bg-yellow-400/20';
      case 'completed': return 'text-green-400 bg-green-400/20';
      case 'cancelled': return 'text-red-400 bg-red-400/20';
      default: return 'text-gray-400 bg-gray-400/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'scheduled': return <Clock className="h-4 w-4" />;
      case 'in-progress': return <Play className="h-4 w-4" />;
      case 'completed': return <CheckCircle className="h-4 w-4" />;
      case 'cancelled': return <XCircle className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#D4AF37] mx-auto mb-4"></div>
          <p className="text-white">Loading interviews...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="bg-black/80 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Link href="/dashboard" className="flex items-center space-x-2 text-white/70 hover:text-white transition-colors">
                <ArrowLeft className="h-5 w-5" />
                <span>Back to Dashboard</span>
              </Link>
            </div>

            <div className="flex items-center space-x-4">
              <Link
                href="/interviews/schedule"
                className="px-4 py-2 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors inline-flex items-center"
              >
                <Plus className="h-4 w-4 mr-2" />
                Schedule Interview
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Interview <span className="text-[#D4AF37]">Management</span>
          </h1>
          <p className="text-white/70">
            Manage your {profile?.role === 'employer' ? 'candidate interviews' : 'job interviews'}
          </p>
        </div>

        {/* Search and Filters */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-white/50" />
            <input
              type="text"
              placeholder="Search interviews..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:border-[#D4AF37] focus:outline-none"
            />
          </div>
          
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:border-[#D4AF37] focus:outline-none"
          >
            <option value="all">All Status</option>
            <option value="scheduled">Scheduled</option>
            <option value="in-progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        {/* Interviews List */}
        <div className="space-y-4">
          {filteredInterviews.length > 0 ? (
            filteredInterviews.map((interview) => (
              <div
                key={interview.id}
                className="bg-white/5 border border-white/10 rounded-xl p-6 hover:border-[#D4AF37] hover:bg-white/10 transition-all duration-300"
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-xl font-semibold text-white mb-2">
                          Interview
                        </h3>
                        <div className="flex items-center space-x-4 text-white/70 text-sm">
                          <div className="flex items-center">
                            <Building className="h-4 w-4 mr-2" />
                            Company
                          </div>
                          <div className="flex items-center">
                            <Calendar className="h-4 w-4 mr-2" />
                            {interview.scheduled_at ? new Date(interview.scheduled_at).toLocaleDateString() : 'TBD'}
                          </div>
                          <div className="flex items-center">
                            <Clock className="h-4 w-4 mr-2" />
                            {interview.scheduled_at ? new Date(interview.scheduled_at).toLocaleTimeString() : 'TBD'}
                          </div>
                        </div>
                      </div>
                      
                      <div className={`px-3 py-1 rounded-full text-sm font-medium flex items-center ${getStatusColor(interview.status || 'scheduled')}`}>
                        {getStatusIcon(interview.status || 'scheduled')}
                        <span className="ml-2 capitalize">{interview.status || 'scheduled'}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div className="flex items-center text-white/70">
                        <Video className="h-4 w-4 mr-2" />
                        <span className="text-sm capitalize">{interview.interview_type || 'Video'} Interview</span>
                      </div>
                      <div className="flex items-center text-white/70">
                        <Clock className="h-4 w-4 mr-2" />
                        <span className="text-sm">{interview.duration_minutes || 30} minutes</span>
                      </div>
                      <div className="flex items-center text-white/70">
                        <User className="h-4 w-4 mr-2" />
                        <span className="text-sm">
                          {profile?.role === 'employer' ? 'Candidate' : 'Interviewer'}
                        </span>
                      </div>
                    </div>

                    {interview.notes && (
                      <div className="mb-4">
                        <p className="text-white/70 text-sm">
                          <strong>Notes:</strong> {interview.notes}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-3 mt-4 lg:mt-0">
                    {interview.status === 'scheduled' && (
                      <Link
                        href={`/interview/${interview.id}`}
                        className="px-4 py-2 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors inline-flex items-center"
                      >
                        <Play className="h-4 w-4 mr-2" />
                        Join Interview
                      </Link>
                    )}
                    
                    {interview.status === 'completed' && (
                      <Link
                        href={`/interview/${interview.id}/analysis`}
                        className="px-4 py-2 bg-white/10 text-white font-semibold rounded-lg hover:bg-white/20 transition-colors inline-flex items-center"
                      >
                        <Eye className="h-4 w-4 mr-2" />
                        View Analysis
                      </Link>
                    )}

                    <Link
                      href={`/interview/${interview.id}/details`}
                      className="px-4 py-2 bg-white/10 text-white font-semibold rounded-lg hover:bg-white/20 transition-colors inline-flex items-center"
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      Details
                    </Link>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-12">
              <Video className="h-16 w-16 text-white/30 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No Interviews Found</h3>
              <p className="text-white/70 mb-6">
                {searchTerm || statusFilter !== 'all' 
                  ? 'Try adjusting your search or filters'
                  : 'You don\'t have any interviews scheduled yet'
                }
              </p>
              {!searchTerm && statusFilter === 'all' && (
                <Link
                  href="/jobs"
                  className="px-6 py-3 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors inline-flex items-center"
                >
                  <ArrowRight className="h-4 w-4 mr-2" />
                  Browse Jobs
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
