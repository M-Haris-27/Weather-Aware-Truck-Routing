# Backend Deployment Guide - Render

## Prerequisites
- GitHub account with your repository pushed
- Render account (sign up at render.com)
- Mapbox Access Token (get free at mapbox.com)

## Step-by-Step Deployment

### 1. Push to GitHub
Make sure all changes are committed and pushed:
```bash
git add .
git commit -m "Prepare backend for production deployment"
git push origin main
```

### 2. Create Web Service on Render

1. Go to https://render.com and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:
   - **Name:** `weather-routing-api` (or your preferred name)
   - **Region:** Choose closest to your users
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn config.wsgi:application`
   - **Instance Type:** `Free` (or paid for better performance)

### 3. Environment Variables

Click **"Advanced"** and add these environment variables:

**Required:**
```
DJANGO_SECRET_KEY=<generate-random-50-char-string>
DJANGO_DEBUG=0
MAPBOX_ACCESS_TOKEN=pk.your_actual_mapbox_token_here
```

**Recommended:**
```
PYTHON_VERSION=3.11.0
ROUTING_PROVIDER=mapbox
GEOCODING_PROVIDER=mapbox
WEATHER_PROVIDER=open_meteo
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
THROTTLE_ANALYZE=30/min
THROTTLE_GEOCODE=120/min
```

> **Note:** You'll update `CORS_ALLOWED_ORIGINS` after deploying the frontend

### 4. Deploy!

Click **"Create Web Service"** - Render will:
- Clone your repository
- Run `build.sh` (install deps, collect static files)
- Start gunicorn server
- Give you a URL like: `https://weather-routing-api.onrender.com`

### 5. Verify Deployment

Once deployed, test the health endpoint:
```bash
curl https://weather-routing-api.onrender.com/api/health
```

Should return:
```json
{
  "status": "ok",
  "providers": {
    "routing": "mapbox",
    "geocoding": "mapbox",
    "weather": "open_meteo"
  }
}
```

### 6. Update CORS After Frontend Deployment

After deploying frontend to Vercel:
1. Go to Render dashboard → Your service → Environment
2. Update `CORS_ALLOWED_ORIGINS` to:
   ```
   https://your-actual-frontend.vercel.app,https://your-actual-frontend-git-main.vercel.app
   ```
3. Save changes (service will auto-redeploy)

## Troubleshooting

**Build fails:**
- Check build logs in Render dashboard
- Verify `build.sh` has execute permissions (should be automatic)
- Ensure all requirements are in `requirements.txt`

**Service crashes on start:**
- Check logs for errors
- Verify `DJANGO_SECRET_KEY` is set
- Verify `MAPBOX_ACCESS_TOKEN` is valid

**CORS errors from frontend:**
- Verify `CORS_ALLOWED_ORIGINS` includes your Vercel URL
- Check browser console for exact origin being blocked
- Remember: Vercel preview deployments have different URLs

**Slow cold starts (Free tier):**
- Render free tier spins down after 15 mins of inactivity
- First request after sleep takes ~30 seconds
- Consider paid tier for always-on service

## Optional: Custom Domain

1. In Render dashboard → Settings → Custom Domain
2. Add your domain
3. Update DNS records as instructed
4. Update `DJANGO_ALLOWED_HOSTS` if needed

## Monitoring

- **Logs:** Render dashboard → Logs tab
- **Metrics:** Render dashboard → Metrics tab  
- **Health check:** Setup at `/api/health`
