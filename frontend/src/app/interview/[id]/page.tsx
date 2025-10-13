'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabase';
import { Interview } from '@/lib/supabase';
import InterviewRoom from '@/components/InterviewRoom';

interface InterviewPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default function InterviewPage({ params }: InterviewPageProps) {
  const router = useRouter();
  const { user, profile, loading: authLoading } = useAuth();
  const [interview, setInterview] = useState<Interview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  
  const fetchInterview = useCallback(async () => {
    try {
      const resolvedParams = await params;
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
        .eq('id', resolvedParams.id)
        .single();

      if (error) throw error;

      // Check if user has access to this interview
      const hasAccess = data.applicant_id === user?.id || data.employer_id === user?.id;
      if (!hasAccess) {
        setError('You do not have access to this interview');
        return;
      }

      setInterview(data);
    } catch (error) {
      console.error('Error fetching interview:', error);
      setError('Failed to load interview details');
    } finally {
      setIsLoading(false);
    }
  }, [user, params]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      fetchInterview();
    }
  }, [user, authLoading, router, params, fetchInterview]);

  const startInterview = async () => {
    setIsStarting(true);
    try {
      const resolvedParams = await params;
      // Update interview status to in-progress
      const { error } = await supabase
        .from('interviews')
        .update({ 
          status: 'in-progress',
          started_at: new Date().toISOString()
        })
        .eq('id', resolvedParams.id);

      if (error) throw error;

      // Start the interview room
      setIsStarting(false);
    } catch (error) {
      console.error('Error starting interview:', error);
      setError('Failed to start interview');
      setIsStarting(false);
    }
  };

  const endInterview = async () => {
    try {
      const resolvedParams = await params;
      // Update interview status to completed
      const { error } = await supabase
        .from('interviews')
        .update({ 
          status: 'completed',
          ended_at: new Date().toISOString()
        })
        .eq('id', resolvedParams.id);

      if (error) throw error;

      // Redirect to interview analysis
      router.push(`/interview/${resolvedParams.id}/analysis`);
    } catch (error) {
      console.error('Error ending interview:', error);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#D4AF37] mx-auto mb-4"></div>
          <p className="text-white">Loading interview...</p>
        </div>
      </div>
    );
  }

  if (error || !interview) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <AlertCircle className="h-16 w-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-4">Interview Not Found</h2>
          <p className="text-white/70 mb-6">{error || 'This interview does not exist or you do not have access to it.'}</p>
          <Link
            href="/interviews"
            className="px-6 py-3 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors inline-flex items-center"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Interviews
          </Link>
        </div>
      </div>
    );
  }

  // If interview is in progress, show the interview room
  if (interview.status === 'in-progress') {
    return (
      <InterviewRoom
        isEmployer={profile?.role === 'employer'}
        onEndInterview={endInterview}
      />
    );
  }

  // Pre-interview setup
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="bg-black/80 backdrop-blur-md border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/interviews" className="flex items-center space-x-2 text-white/70 hover:text-white transition-colors">
              <ArrowLeft className="h-5 w-5" />
              <span>Back to Interviews</span>
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Interview Details */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">
            Interview
          </h1>
          <p className="text-xl text-white/70 mb-8">
            with Company
          </p>

          <div className="flex items-center justify-center space-x-8 text-white/70">
            <div className="text-center">
              <div className="text-2xl font-bold text-[#D4AF37]">
                {interview.scheduled_at ? new Date(interview.scheduled_at).toLocaleDateString() : 'TBD'}
              </div>
              <div className="text-sm">Date</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-[#D4AF37]">
                {interview.scheduled_at ? new Date(interview.scheduled_at).toLocaleTimeString() : 'TBD'}
              </div>
              <div className="text-sm">Time</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-[#D4AF37]">
                {interview.duration_minutes || 30}
              </div>
              <div className="text-sm">Minutes</div>
            </div>
          </div>
        </div>

        {/* Interview Status */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-8 mb-8">
          <div className="text-center">
            <div className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-medium mb-4 ${
              interview.status === 'scheduled' ? 'text-blue-400 bg-blue-400/20' :
              interview.status === 'completed' ? 'text-green-400 bg-green-400/20' :
              interview.status === 'cancelled' ? 'text-red-400 bg-red-400/20' :
              'text-gray-400 bg-gray-400/20'
            }`}>
              {interview.status === 'scheduled' ? <CheckCircle className="h-4 w-4 mr-2" /> : null}
              <span className="capitalize">{interview.status}</span>
      </div>

            {interview.status === 'scheduled' && (
              <div className="space-y-4">
                <h3 className="text-xl font-semibold mb-4">Ready to Start?</h3>
                <p className="text-white/70 mb-6">
                  Make sure you have a good internet connection and your camera/microphone are working properly.
                </p>
                
                <button
                  onClick={startInterview}
                  disabled={isStarting}
                  className="px-8 py-4 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isStarting ? 'Starting...' : 'Start Interview'}
                </button>
              </div>
            )}

            {interview.status === 'completed' && (
              <div className="space-y-4">
                <h3 className="text-xl font-semibold mb-4">Interview Completed</h3>
                <p className="text-white/70 mb-6">
                  Thank you for completing the interview. You can view the analysis and feedback below.
                </p>
                
                <Link
                  href={`/interview/${interview.id}/analysis`}
                  className="px-8 py-4 bg-[#D4AF37] text-black font-semibold rounded-lg hover:bg-[#C49F2F] transition-colors inline-flex items-center"
                >
                  View Analysis
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Interview Information */}
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Interview Details</h3>
            <div className="space-y-3">
              <div>
                <span className="text-white/70">Type:</span>
                <span className="ml-2 capitalize">{interview.interview_type || 'Video'}</span>
                </div>
              <div>
                <span className="text-white/70">Duration:</span>
                <span className="ml-2">{interview.duration_minutes || 30} minutes</span>
              </div>
              <div>
                <span className="text-white/70">Meeting Link:</span>
                <span className="ml-2 text-[#D4AF37]">
                  {interview.meeting_link || 'Will be provided when interview starts'}
                        </span>
                        </div>
                      </div>
                    </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Preparation Tips</h3>
            <ul className="space-y-2 text-white/70 text-sm">
              <li>• Test your camera and microphone</li>
              <li>• Ensure good lighting</li>
              <li>• Find a quiet environment</li>
              <li>• Have your resume ready</li>
              <li>• Prepare questions to ask</li>
            </ul>
                    </div>
                  </div>

        {interview.notes && (
          <div className="mt-6 bg-white/5 border border-white/10 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Additional Notes</h3>
            <p className="text-white/70">{interview.notes}</p>
          </div>
        )}
      </div>
    </div>
  );
} 
