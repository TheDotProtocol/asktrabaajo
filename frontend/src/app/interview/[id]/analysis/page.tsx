'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft,
  BarChart3,
  Smile,
  Clock,
  User,
  TrendingUp,
  TrendingDown,
  Eye,
  Brain,
  Download,
  Share,
  CheckCircle
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabase';
import { Interview } from '@/lib/supabase';

interface InterviewAnalysisProps {
  params: Promise<{
    id: string;
  }>;
}

interface AnalysisData {
  overallScore: number;
  duration: number;
  keyStrengths: string[];
  areasForImprovement: string[];
  sentimentAnalysis: {
    positive: number;
    neutral: number;
    negative: number;
  };
  technicalSkills: Record<string, number>;
  behavioralTraits: Record<string, number>;
  recommendations: string[];
}

export default function InterviewAnalysis({ params }: InterviewAnalysisProps) {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [interview, setInterview] = useState<Interview | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchInterviewData = useCallback(async () => {
    try {
      const resolvedParams = await params;
      // Fetch interview details
      const { data: interviewData, error: interviewError } = await supabase
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

      if (interviewError) throw interviewError;
      setInterview(interviewData);

      // Generate mock analysis data (in real app, this would come from AI analysis)
      const mockAnalysis: AnalysisData = {
        overallScore: 85,
        duration: 45,
        keyStrengths: [
          'Strong technical knowledge',
          'Good communication skills',
          'Problem-solving approach',
          'Cultural fit'
        ],
        areasForImprovement: [
          'Could elaborate more on experience',
          'Ask more questions about the role'
        ],
        sentimentAnalysis: {
          positive: 75,
          neutral: 20,
          negative: 5
        },
        technicalSkills: {
          'JavaScript': 90,
          'React': 85,
          'Node.js': 80,
          'Database Design': 75
        },
        behavioralTraits: {
          'Confidence': 88,
          'Communication': 82,
          'Problem Solving': 85,
          'Teamwork': 78
        },
        recommendations: [
          'Strong candidate for the role',
          'Consider for next round',
          'Good cultural fit',
          'Technical skills align with requirements'
        ]
      };

      setAnalysis(mockAnalysis);
    } catch (error) {
      console.error('Error fetching interview data:', error);
    } finally {
      setIsLoading(false);
    }
  }, [params]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      fetchInterviewData();
    }
  }, [user, authLoading, router, fetchInterviewData]);

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#D4AF37] mx-auto mb-4"></div>
          <p className="text-white">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (!interview || !analysis) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-4">Analysis Not Available</h2>
          <p className="text-white/70 mb-6">This interview analysis is not available yet.</p>
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
            
            <div className="flex items-center space-x-4">
              <button className="p-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors">
                <Download className="h-5 w-5" />
              </button>
              <button className="p-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors">
                <Share className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Interview Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Interview <span className="text-[#D4AF37]">Analysis</span>
          </h1>
          <p className="text-white/70">
            Interview Analysis
          </p>
        </div>

        {/* Overall Score */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-8 mb-8">
          <div className="text-center">
            <div className="text-6xl font-bold text-[#D4AF37] mb-4">
              {analysis.overallScore}%
            </div>
            <h2 className="text-2xl font-semibold mb-2">Overall Performance</h2>
            <p className="text-white/70">
              {analysis.overallScore >= 80 ? 'Excellent' : 
               analysis.overallScore >= 60 ? 'Good' : 
               analysis.overallScore >= 40 ? 'Fair' : 'Needs Improvement'}
            </p>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="flex items-center mb-4">
              <Clock className="h-6 w-6 text-[#D4AF37] mr-3" />
              <h3 className="text-lg font-semibold">Duration</h3>
            </div>
            <div className="text-2xl font-bold text-white">{analysis.duration} minutes</div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="flex items-center mb-4">
              <Smile className="h-6 w-6 text-[#D4AF37] mr-3" />
              <h3 className="text-lg font-semibold">Sentiment</h3>
            </div>
            <div className="text-2xl font-bold text-white">{analysis.sentimentAnalysis.positive}% Positive</div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="flex items-center mb-4">
              <Brain className="h-6 w-6 text-[#D4AF37] mr-3" />
              <h3 className="text-lg font-semibold">AI Analysis</h3>
            </div>
            <div className="text-2xl font-bold text-white">Complete</div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Strengths */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <h3 className="text-xl font-semibold mb-4 flex items-center">
              <TrendingUp className="h-6 w-6 text-green-400 mr-3" />
              Key Strengths
            </h3>
            <ul className="space-y-3">
              {analysis.keyStrengths.map((strength: string, index: number) => (
                <li key={index} className="flex items-start">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3 mt-0.5 flex-shrink-0" />
                  <span className="text-white/80">{strength}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Areas for Improvement */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <h3 className="text-xl font-semibold mb-4 flex items-center">
              <TrendingDown className="h-6 w-6 text-yellow-400 mr-3" />
              Areas for Improvement
            </h3>
            <ul className="space-y-3">
              {analysis.areasForImprovement.map((area: string, index: number) => (
                <li key={index} className="flex items-start">
                  <div className="h-5 w-5 border-2 border-yellow-400 rounded-full mr-3 mt-0.5 flex-shrink-0"></div>
                  <span className="text-white/80">{area}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Technical Skills */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-6 mb-8">
          <h3 className="text-xl font-semibold mb-6 flex items-center">
            <BarChart3 className="h-6 w-6 text-[#D4AF37] mr-3" />
            Technical Skills Assessment
          </h3>
          <div className="space-y-4">
            {Object.entries(analysis.technicalSkills).map(([skill, score]) => (
              <div key={skill}>
                <div className="flex justify-between mb-2">
                  <span className="text-white/80">{skill}</span>
                  <span className="text-[#D4AF37] font-semibold">{score}%</span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-2">
                  <div 
                    className="bg-[#D4AF37] h-2 rounded-full transition-all duration-500"
                    style={{ width: `${score}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Behavioral Traits */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-6 mb-8">
          <h3 className="text-xl font-semibold mb-6 flex items-center">
            <User className="h-6 w-6 text-[#D4AF37] mr-3" />
            Behavioral Traits
          </h3>
          <div className="space-y-4">
            {Object.entries(analysis.behavioralTraits).map(([trait, score]) => (
              <div key={trait}>
                <div className="flex justify-between mb-2">
                  <span className="text-white/80">{trait}</span>
                  <span className="text-[#D4AF37] font-semibold">{score}%</span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-2">
                  <div 
                    className="bg-[#D4AF37] h-2 rounded-full transition-all duration-500"
                    style={{ width: `${score}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-6">
          <h3 className="text-xl font-semibold mb-6 flex items-center">
            <Eye className="h-6 w-6 text-[#D4AF37] mr-3" />
            AI Recommendations
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            {analysis.recommendations.map((recommendation: string, index: number) => (
              <div key={index} className="flex items-start p-4 bg-white/5 rounded-lg">
                <div className="h-6 w-6 bg-[#D4AF37] rounded-full flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                  <span className="text-black text-sm font-bold">{index + 1}</span>
                </div>
                <span className="text-white/80">{recommendation}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
