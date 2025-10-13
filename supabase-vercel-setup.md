# Supabase + Vercel Setup Guide for AskTrabaajo

## 🚀 Step-by-Step Setup

### Step 1: Create New Supabase Account
1. **Go to [supabase.com](https://supabase.com)**
2. **Click "Start your project"**
3. **Sign up with NEW Gmail account** (e.g., asktrabaajo@gmail.com)
4. **Verify email address**
5. **Create new organization** (e.g., "AskTrabaajo Corp")

### Step 2: Create Supabase Project
1. **Click "New Project"**
2. **Choose organization**: AskTrabaajo Corp
3. **Project name**: asktrabaajo-production
4. **Database password**: Generate strong password (save it!)
5. **Region**: Choose closest to your users
6. **Click "Create new project"**
7. **Wait for setup to complete** (2-3 minutes)

### Step 3: Get Database Credentials
1. **Go to Settings → Database**
2. **Copy the connection string** (looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
3. **Save this for later use**

### Step 4: Set Up Database Schema
1. **Go to SQL Editor in Supabase**
2. **Create tables using your existing schema**
3. **Or import from your current database**

### Step 5: Configure Supabase Auth
1. **Go to Authentication → Settings**
2. **Site URL**: `https://your-vercel-domain.vercel.app`
3. **Redirect URLs**: Add your frontend URLs
4. **Enable email auth** (using your tauos/taumail)

### Step 6: Deploy to Vercel
1. **Go to [vercel.com](https://vercel.com)**
2. **Sign up with GitHub**
3. **Import your asktrabaajo repository**
4. **Set root directory to `frontend`**
5. **Deploy**

### Step 7: Configure Environment Variables

#### Vercel Environment Variables:
```bash
# Frontend Environment Variables
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://your-vercel-backend.vercel.app
```

#### Backend Environment Variables (if deploying backend to Vercel):
```bash
# Database
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Supabase
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# JWT
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256

# Email (Your existing tauos/taumail)
EMAIL_HOST=your-tauos-smtp-host
EMAIL_PORT=587
EMAIL_USER=your-tauos-email-user
EMAIL_PASS=your-tauos-email-password
EMAIL_USE_TLS=true
EMAIL_FROM=noreply@asktrabaajo.com

# OpenAI
OPENAI_API_KEY=your-openai-key

# CORS
CORS_ORIGINS=https://your-vercel-domain.vercel.app
```

## 🔧 Backend Deployment Options

### Option A: Vercel Functions (Recommended)
- Deploy backend as Vercel serverless functions
- Automatic scaling
- No server management
- Integrated with frontend

### Option B: Railway Backend + Vercel Frontend
- Railway for backend API
- Vercel for frontend
- More control over backend
- Better for complex backend logic

## 🎯 Benefits of Supabase + Vercel

### ✅ Supabase Benefits:
- **PostgreSQL Database**: Full-featured SQL database
- **Built-in Auth**: User authentication and management
- **Real-time**: WebSocket connections for live updates
- **Storage**: File uploads and management
- **Edge Functions**: Serverless functions
- **Free Tier**: 500MB database, 2GB bandwidth

### ✅ Vercel Benefits:
- **Frontend Hosting**: Optimized for Next.js
- **Global CDN**: Fast loading worldwide
- **Automatic Deployments**: Git-based deployments
- **Preview Deployments**: Test before production
- **Analytics**: Performance monitoring
- **Free Tier**: Unlimited static hosting

## 🚀 Quick Start Commands

### Install Supabase CLI (Optional):
```bash
npm install -g supabase
supabase login
supabase init
```

### Update Frontend for Supabase:
```bash
# Install Supabase client
npm install @supabase/supabase-js

# Create Supabase client
# src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

## 🔧 Database Migration

### Option 1: Manual Setup
1. **Go to Supabase SQL Editor**
2. **Run your database schema**
3. **Create tables and relationships**

### Option 2: Import from Existing
1. **Export your current database**
2. **Import to Supabase**
3. **Update connection strings**

## 📊 Monitoring & Analytics

### Supabase Dashboard:
- Database performance
- API usage
- Auth analytics
- Storage usage
- Real-time connections

### Vercel Dashboard:
- Frontend performance
- Build analytics
- Function logs
- Edge network metrics

## 🎯 Next Steps After Setup

1. **Test the connection** between frontend and Supabase
2. **Set up authentication** flow
3. **Configure email templates** in Supabase
4. **Set up file storage** for documents
5. **Configure real-time subscriptions**
6. **Set up monitoring** and alerts

This setup gives you a production-ready, scalable infrastructure with excellent developer experience!
