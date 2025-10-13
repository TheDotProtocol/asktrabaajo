-- AskTrabaajo Database Schema for Supabase
-- Run this in your Supabase SQL Editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (extends Supabase auth.users)
CREATE TABLE public.profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  first_name TEXT,
  last_name TEXT,
  role TEXT NOT NULL CHECK (role IN ('jobseeker', 'employer', 'hr_consultant', 'government', 'foreign_company')),
  company_name TEXT,
  phone TEXT,
  location TEXT,
  bio TEXT,
  skills TEXT[],
  experience JSONB,
  education JSONB,
  certifications JSONB,
  desired_salary TEXT,
  preferred_locations TEXT[],
  remote_preference BOOLEAN DEFAULT false,
  government_id TEXT,
  department TEXT,
  country TEXT,
  business_license TEXT,
  tax_id TEXT,
  is_verified BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Jobs table
CREATE TABLE public.jobs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  employer_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  requirements TEXT[],
  skills_required TEXT[],
  location TEXT,
  remote_allowed BOOLEAN DEFAULT false,
  salary_min INTEGER,
  salary_max INTEGER,
  currency TEXT DEFAULT 'USD',
  employment_type TEXT CHECK (employment_type IN ('full-time', 'part-time', 'contract', 'internship')),
  experience_level TEXT CHECK (experience_level IN ('entry', 'mid', 'senior', 'executive')),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'closed')),
  application_deadline TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Applications table
CREATE TABLE public.applications (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id UUID REFERENCES public.jobs(id) ON DELETE CASCADE,
  applicant_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'applied' CHECK (status IN ('applied', 'reviewed', 'shortlisted', 'interviewed', 'rejected', 'hired')),
  cover_letter TEXT,
  resume_url TEXT,
  applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(job_id, applicant_id)
);

-- Interviews table
CREATE TABLE public.interviews (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  job_id UUID REFERENCES public.jobs(id) ON DELETE CASCADE,
  applicant_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  employer_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  scheduled_at TIMESTAMP WITH TIME ZONE,
  duration_minutes INTEGER DEFAULT 30,
  interview_type TEXT CHECK (interview_type IN ('video', 'phone', 'in-person')),
  status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in-progress', 'completed', 'cancelled')),
  meeting_link TEXT,
  notes TEXT,
  feedback JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Test Results table
CREATE TABLE public.test_results (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  job_id UUID REFERENCES public.jobs(id) ON DELETE CASCADE,
  test_type TEXT NOT NULL,
  score INTEGER,
  max_score INTEGER,
  results JSONB,
  completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payments table
CREATE TABLE public.payments (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  amount DECIMAL(10,2) NOT NULL,
  currency TEXT DEFAULT 'USD',
  payment_method TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
  transaction_id TEXT,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Notifications table
CREATE TABLE public.notifications (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  type TEXT CHECK (type IN ('info', 'success', 'warning', 'error')),
  read BOOLEAN DEFAULT false,
  data JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents table
CREATE TABLE public.documents (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  file_url TEXT NOT NULL,
  file_type TEXT,
  file_size INTEGER,
  document_type TEXT CHECK (document_type IN ('resume', 'cover_letter', 'certificate', 'portfolio', 'other')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_profiles_role ON public.profiles(role);
CREATE INDEX idx_profiles_email ON public.profiles(email);
CREATE INDEX idx_jobs_employer ON public.jobs(employer_id);
CREATE INDEX idx_jobs_status ON public.jobs(status);
CREATE INDEX idx_applications_job ON public.applications(job_id);
CREATE INDEX idx_applications_applicant ON public.applications(applicant_id);
CREATE INDEX idx_interviews_applicant ON public.interviews(applicant_id);
CREATE INDEX idx_notifications_user ON public.notifications(user_id);
CREATE INDEX idx_notifications_read ON public.notifications(read);

-- Row Level Security (RLS) policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- Jobs policies
CREATE POLICY "Anyone can view active jobs" ON public.jobs FOR SELECT USING (status = 'active');
CREATE POLICY "Employers can manage their jobs" ON public.jobs FOR ALL USING (auth.uid() = employer_id);

-- Applications policies
CREATE POLICY "Users can view own applications" ON public.applications FOR SELECT USING (auth.uid() = applicant_id OR auth.uid() IN (SELECT employer_id FROM public.jobs WHERE id = job_id));
CREATE POLICY "Users can create applications" ON public.applications FOR INSERT WITH CHECK (auth.uid() = applicant_id);

-- Interviews policies
CREATE POLICY "Users can view own interviews" ON public.interviews FOR SELECT USING (auth.uid() = applicant_id OR auth.uid() = employer_id);
CREATE POLICY "Employers can manage interviews" ON public.interviews FOR ALL USING (auth.uid() = employer_id);

-- Test results policies
CREATE POLICY "Users can view own test results" ON public.test_results FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own test results" ON public.test_results FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Payments policies
CREATE POLICY "Users can view own payments" ON public.payments FOR SELECT USING (auth.uid() = user_id);

-- Notifications policies
CREATE POLICY "Users can view own notifications" ON public.notifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own notifications" ON public.notifications FOR UPDATE USING (auth.uid() = user_id);

-- Documents policies
CREATE POLICY "Users can view own documents" ON public.documents FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own documents" ON public.documents FOR ALL USING (auth.uid() = user_id);

-- Functions
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, first_name, last_name, role)
  VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'first_name', NEW.raw_user_meta_data->>'last_name', COALESCE(NEW.raw_user_meta_data->>'role', 'jobseeker'));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for new user creation
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Update timestamp function
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add update triggers
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON public.jobs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON public.applications FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_interviews_updated_at BEFORE UPDATE ON public.interviews FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
