# Deployment to Render

## Prerequisites
- GitHub account (to host your code)
- Render account (free tier available at https://render.com)

## Step-by-Step Deployment Guide

### 1. Push Your Code to GitHub

```bash
git init
git add .
git commit -m "Initial commit for Render deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/exam-administration-system.git
git push -u origin main
```

### 2. Connect Render to Your GitHub Repository

1. Go to [https://render.com](https://render.com)
2. Sign in or create an account
3. Click **New +** and select **Web Service**
4. Select **Deploy an existing repository** or **Build and deploy from a Git repository**
5. Authorize Render to access your GitHub account

### 3. Configure Your Web Service on Render

Fill in the deployment settings:

- **Name**: `exam-administration-system`
- **Region**: Choose your closest region
- **Branch**: `main`
- **Runtime**: `Python 3.11`
- **Build Command**: 
  ```
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```
  gunicorn app:app
  ```

### 4. Add Environment Variables (if needed)

In the Render dashboard under **Environment**:
- No mandatory environment variables for basic deployment
- PORT is automatically set by Render (default: 10000)

### 5. Deploy

Click **Create Web Service**. Render will:
1. Build your app (install dependencies)
2. Start the application with gunicorn
3. Assign you a URL like `https://exam-administration-system.onrender.com`

### 6. Monitor Deployment

- Watch the **Logs** tab to see if deployment is successful
- Look for messages like "Application startup complete"
- Your app will be available at the assigned URL

## Important Notes

### File Storage
- Your `database/` and `schedule_storage/` folders are **ephemeral** on the free tier
- Files will be reset when the service restarts
- **Solution**: Upgrade to Paid tier with persistent storage, or use external database (PostgreSQL, etc.)

### Performance
- Free tier includes auto-sleep after 15 minutes of inactivity
- First request after sleep may take 30 seconds
- Upgrade to Pro for better performance

### Database Persistence
For production use, consider:
1. **PostgreSQL** (available on Render)
2. **Cloud Storage** (AWS S3, Google Cloud Storage)
3. Modify your app to use persistent storage instead of local files

## Troubleshooting

### "Python version not found"
- Ensure `runtime.txt` or Python version is specified

### "Module not found" errors
- Check `requirements.txt` has all dependencies
- Verify imports match installed packages

### "Address already in use"
- Render automatically manages ports
- Don't hardcode port 5000; use the PORT environment variable (already updated in app.py)

### Application crashes
- Check logs in Render dashboard
- Look for startup errors in Logs tab

## Next Steps

1. Test the application thoroughly in the browser
2. Set up error monitoring
3. Configure custom domain (if desired)
4. Consider upgrading to Paid tier for persistent storage
5. Set up automated deployments (GitHub push = auto-deploy)

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
