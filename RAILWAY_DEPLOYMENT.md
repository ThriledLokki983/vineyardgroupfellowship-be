# Railway Deployment Guide for Vineyard Group Fellowship

## 🚂 Railway Setup Steps

### 1. Create Railway Project
1. Go to [railway.app](https://railway.app)
2. Create new project from GitHub repo: `ThriledLokki983/vineyardgroupfellowship-be`

### 2. Add PostgreSQL Database
1. In Railway dashboard, click "Add Service"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create these environment variables:
   ```
   DATABASE_URL=postgresql://user:password@host:port/database
   PGHOST=hostname
   PGDATABASE=database_name
   PGUSER=username
   PGPASSWORD=password
   PGPORT=5432
   ```

### 3. Configure Environment Variables
In Railway dashboard, add these additional variables:

#### Required for Django
```bash
DJANGO_SETTINGS_MODULE=vineyard_group_fellowship.settings.production
RAILWAY_ENVIRONMENT=production
SECRET_KEY=your-super-secret-production-key-here
```

#### Email Configuration (SendGrid)
```bash
SENDGRID_API_KEY=SG.your_sendgrid_api_key_here
DEFAULT_FROM_EMAIL=noreply@vineyardgroupfellowship.org
SUPPORT_EMAIL=support@vineyardgroupfellowship.org
```

#### Optional - Custom Domain
```bash
CUSTOM_DOMAIN=your-custom-domain.com
```

#### Optional - Sentry Error Tracking
```bash
SENTRY_DSN=https://your-sentry-dsn-here
```

### 4. Railway Build Configuration

Railway should auto-detect your build process, but you can add a `railway.json`:

```json
{
  "build": {
    "command": "pip install -r requirements.txt"
  },
  "start": {
    "command": "./start.sh"
  }
}
```

### 5. Domain Configuration

After deployment:
1. Railway provides a public URL: `your-app.up.railway.app`
2. Configure custom domain in Railway dashboard
3. Update `ALLOWED_HOSTS` in production.py if needed

## 🔧 Troubleshooting

### Database Connection Issues
If you see "Name or service not known":
1. Ensure PostgreSQL service is running in Railway
2. Check environment variables are set correctly
3. Verify `DATABASE_URL` is available

### Migration Issues
```bash
# Manual migration (if needed)
railway run python manage.py migrate
```

### View Logs
```bash
railway logs
```

## 🚀 Deployment Checklist

- [ ] PostgreSQL service added to Railway project
- [ ] Environment variables configured
- [ ] SendGrid API key added (if using email)
- [ ] SECRET_KEY set to production value
- [ ] Domain configured (if using custom domain)
- [ ] First deployment successful
- [ ] Database migrations completed
- [ ] Admin user created

## 📝 Post-Deployment

1. **Create superuser:**
   ```bash
   railway run python manage.py createsuperuser
   ```

2. **Test API endpoints:**
   - Health check: `https://your-app.up.railway.app/api/v1/auth/health/`
   - API docs: `https://your-app.up.railway.app/api/docs/`

3. **Monitor logs:**
   ```bash
   railway logs --follow
   ```