# Render + Supabase Deployment Guide

## ✅ Configuration Set Up

Your UNIGOM Biometric System is now configured for **Render** (hosting) + **Supabase** (PostgreSQL database) testing.

## 📋 Current Setup

- **Database**: Supabase PostgreSQL
- **URL**: https://abjlfxnvepxfazsagxtu.supabase.co
- **Hosting**: Render (ready to deploy)
- **Backend Framework**: FastAPI + Uvicorn

## 🚀 Deploy to Render

### Step 1: Connect GitHub Repository
1. Go to https://render.com/dashboard
2. Click "New +" → "Web Service"
3. Select "Connect a GitHub repository"
4. Choose: `nathanael10142/biometric-unigom`
5. Branch: `main`

### Step 2: Configure Render Service
- **Name**: `unigom-biometric-backend`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt && python render_deploy.py`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- **Plan**: Free (or Starter)

### Step 3: Set Environment Variables
Add these in Render Dashboard under "Environment":

```
DATABASE_URL=postgresql://postgres.abjlfxnvepxfazsagxtu:mGwH1hb9IeAJ1KO2193LACV6lQFwcpMoKfM996KFBJA@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://abjlfxnvepxfazsagxtu.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiamxmeG52ZXB4ZmF6c2FneHR1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzIyODc0NiwiZXhwIjoyMDg4ODA0NzQ2fQ.mGwH1hb9IeAJ1KO2193LACV6lQFwcpMoKfM996KFBJA
JWT_SECRET_KEY=your-super-secret-key-here
DEBUG=False
ENVIRONMENT=production
CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.vercel.app
```

### Step 4: Deploy
Click "Create Web Service" and wait for deployment!

## 📊 Your API will be available at:
- **Base URL**: `https://unigom-biometric-backend.onrender.com`
- **API Docs**: `https://unigom-biometric-backend.onrender.com/docs`
- **ReDoc**: `https://unigom-biometric-backend.onrender.com/redoc`
- **Health Check**: `https://unigom-biometric-backend.onrender.com/health`

## 🔍 Monitoring

### Check Logs
1. Go to your Render dashboard
2. Select the web service
3. Click "Logs" tab to see real-time output

### Health Status
```bash
curl https://unigom-biometric-backend.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-11T10:30:00Z",
  "environment": "production",
  "version": "1.0.0"
}
```

## 🔑 Key Files for Deployment

- `.env` - Environment variables (contains Supabase credentials)
- `render.yaml` - Render configuration
- `render_deploy.py` - Database initialization script
- `requirements.txt` - Python dependencies (includes psycopg2 for PostgreSQL)

## ⚠️ Important Notes

1. **Security**: The `.env` file contains sensitive credentials. Never commit it to GitHub in a real scenario.
2. **Credentials in Code**: For testing only. Move to Render environment variables for production.
3. **Database Reset**: If you need to reset the database, delete the PostgreSQL instance on Supabase and redeploy.
4. **Custom Domain**: Render supports custom domains. Add yours under "Settings" → "Domain".

## 🛠️ Troubleshooting

### Database Connection Error
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```
- Check `DATABASE_URL` in Render environment variables
- Verify Supabase instance is running
- Check firewall rules on Supabase

### Import Errors
```
ModuleNotFoundError: No module named 'psycopg2'
```
- Ensure `requirements.txt` includes `psycopg2-binary`
- Check build command runs `pip install -r requirements.txt`

### Build Failures
- Check the build logs in Render dashboard
- Ensure all Python dependencies are in `requirements.txt`
- Verify `render_deploy.py` is executable

## 📝 Next Steps

1. **Deploy to Render** (follow steps above)
2. **Test API endpoints** using the `/docs` Swagger UI
3. **Frontend Integration**: Update frontend API URL to your Render URL
4. **Production Database**: Consider migrating from Supabase free tier to a dedicated instance when ready

## 🎯 API Endpoints to Test

- `GET /health` - Server health check
- `POST /auth/login` - Login
- `GET /employees` - List employees
- `POST /attendance` - Record attendance
- `GET /dashboard` - Dashboard data

---

**Status**: ✅ Ready for deployment to Render + Supabase
**Last Updated**: March 11, 2026
