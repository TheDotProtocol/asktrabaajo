import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Database types
export interface Profile {
  id: string
  email: string
  first_name?: string
  last_name?: string
  role: 'jobseeker' | 'employer' | 'hr_consultant' | 'government' | 'foreign_company'
  company_name?: string
  phone?: string
  location?: string
  bio?: string
  skills?: string[]
  experience?: any[]
  education?: any[]
  certifications?: any[]
  desired_salary?: string
  preferred_locations?: string[]
  remote_preference?: boolean
  government_id?: string
  department?: string
  country?: string
  business_license?: string
  tax_id?: string
  is_verified?: boolean
  created_at?: string
  updated_at?: string
}

export interface Job {
  id: string
  employer_id: string
  title: string
  description: string
  requirements?: string[]
  skills_required?: string[]
  location?: string
  remote_allowed?: boolean
  salary_min?: number
  salary_max?: number
  currency?: string
  employment_type?: 'full-time' | 'part-time' | 'contract' | 'internship'
  experience_level?: 'entry' | 'mid' | 'senior' | 'executive'
  status?: 'active' | 'paused' | 'closed'
  application_deadline?: string
  created_at?: string
  updated_at?: string
}

export interface Application {
  id: string
  job_id: string
  applicant_id: string
  status?: 'applied' | 'reviewed' | 'shortlisted' | 'interviewed' | 'rejected' | 'hired'
  cover_letter?: string
  resume_url?: string
  applied_at?: string
  updated_at?: string
}

export interface Interview {
  id: string
  job_id: string
  applicant_id: string
  employer_id: string
  scheduled_at?: string
  duration_minutes?: number
  interview_type?: 'video' | 'phone' | 'in-person'
  status?: 'scheduled' | 'in-progress' | 'completed' | 'cancelled'
  meeting_link?: string
  notes?: string
  feedback?: any
  created_at?: string
  updated_at?: string
}

export interface TestResult {
  id: string
  user_id: string
  job_id?: string
  test_type: string
  score?: number
  max_score?: number
  results?: any
  completed_at?: string
}

export interface Payment {
  id: string
  user_id: string
  amount: number
  currency?: string
  payment_method?: string
  status?: 'pending' | 'completed' | 'failed' | 'refunded'
  transaction_id?: string
  description?: string
  created_at?: string
}

export interface Notification {
  id: string
  user_id: string
  title: string
  message: string
  type?: 'info' | 'success' | 'warning' | 'error'
  read?: boolean
  data?: any
  created_at?: string
}

export interface Document {
  id: string
  user_id: string
  filename: string
  file_url: string
  file_type?: string
  file_size?: number
  document_type?: 'resume' | 'cover_letter' | 'certificate' | 'portfolio' | 'other'
  created_at?: string
}
