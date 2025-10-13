# Railway Setup Guide for AskTrabaajo

## 🚀 Quick Railway Setup

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Connect your `asktrabaajo` repository

### Step 2: Add PostgreSQL Database
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your `asktrabaajo` repository
4. Click "Add Service" → "Database" → "PostgreSQL"
5. Copy the connection string

### Step 3: Deploy Backend
1. Add another service → "GitHub Repo"
2. Select your repository
3. Set root directory to `backend`
4. Configure environment variables

### Step 4: Environment Variables
```bash
# Database
DATABASE_URL=postgresql://postgres:password@host:port/railway

# JWT
JWT_SECRET=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Email (Your existing setup)
EMAIL_HOST=your-tauos-smtp-host
EMAIL_PORT=587
EMAIL_USER=your-tauos-email-user
EMAIL_PASS=your-tauos-email-password
EMAIL_USE_TLS=true
EMAIL_FROM=noreply@asktrabaajo.com

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# CORS
CORS_ORIGINS=https://your-vercel-domain.vercel.app,http://localhost:3000

# WebRTC (Optional)
TURN_SERVER_URL=your-turn-server
TURN_USERNAME=your-turn-username
TURN_CREDENTIAL=your-turn-credential
```

### Step 5: Deploy Frontend to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Set root directory to `frontend`
4. Deploy

### Step 6: Update Frontend API URLs
```typescript
// In your frontend, update API base URL
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-railway-backend.railway.app' 
  : 'http://localhost:8000';
```

## 🔧 Production Environment Files

### Backend .env.production
```bash
# Database
DATABASE_URL=postgresql://postgres:password@host:port/railway

# Security
JWT_SECRET=your-production-jwt-secret
SECRET_KEY=your-production-secret-key

# Email (Your existing infrastructure)
EMAIL_HOST=your-tauos-smtp-host
EMAIL_PORT=587
EMAIL_USER=your-tauos-email-user
EMAIL_PASS=your-tauos-email-password
EMAIL_USE_TLS=true
EMAIL_FROM=noreply@asktrabaajo.com

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# CORS
CORS_ORIGINS=https://asktrabaajo.vercel.app

# WebRTC
TURN_SERVER_URL=your-turn-server
TURN_USERNAME=your-turn-username
TURN_CREDENTIAL=your-turn-credential

# Monitoring
SENTRY_DSN=your-sentry-dsn
```

### Frontend .env.production
```bash
NEXT_PUBLIC_API_URL=https://your-railway-backend.railway.app
NEXT_PUBLIC_APP_URL=https://asktrabaajo.vercel.app
```

## 🎯 Benefits of This Setup

### ✅ Cost Effective
- **Railway**: Free tier (1GB database, 512MB RAM)
- **Vercel**: Free tier (unlimited static hosting)
- **Email**: Your existing infrastructure (free)

### ✅ Scalable
- Easy to upgrade Railway plan when needed
- Automatic scaling
- Global CDN via Vercel

### ✅ Professional
- Custom domains
- SSL certificates
- Environment management
- Automatic deployments

## 🚀 Deployment Commands

### Railway CLI (Optional)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up
```

### Manual Deployment
1. Push to GitHub
2. Railway auto-deploys
3. Vercel auto-deploys
4. Update DNS if using custom domain

## 🔧 Next Steps After Setup

1. **Test the deployment**
2. **Configure custom domain** (optional)
3. **Set up monitoring** (Sentry, LogRocket)
4. **Configure backups** (Railway provides automatic backups)
5. **Set up staging environment** (optional)

## 📊 Monitoring & Maintenance

### Railway Dashboard
- Database metrics
- API performance
- Error logs
- Resource usage

### Vercel Dashboard
- Frontend performance
- Build logs
- Analytics
- Function logs

This setup gives you a production-ready, scalable infrastructure at minimal cost!
