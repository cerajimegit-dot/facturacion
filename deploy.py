#!/usr/bin/env python
"""Automated deployment script for Vercel + Supabase."""
import os
import sys
import subprocess
import json

def run_command(cmd, cwd=None):
    """Run command and return result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False, result.stderr
    return True, result.stdout

def check_requirements():
    """Check if required tools are installed."""
    print("Checking requirements...")
    
    # Check git
    success, _ = run_command("git --version")
    if not success:
        print("❌ Git not found. Please install Git.")
        return False
    
    # Check Vercel CLI
    success, _ = run_command("vercel --version")
    if not success:
        print("❌ Vercel CLI not found. Please install: npm i -g vercel")
        return False
    
    print("✅ All requirements met")
    return True

def prepare_git():
    """Prepare git repository."""
    print("Preparing git repository...")
    
    # Add all changes
    run_command("git add -A")
    
    # Commit changes
    success, _ = run_command('git commit -m "feat: Prepare for Vercel + Supabase deployment"')
    if success:
        print("✅ Changes committed")
    else:
        print("ℹ️ No changes to commit")
    
    return True

def deploy_backend():
    """Deploy backend to Vercel."""
    print("Deploying backend to Vercel...")
    
    # Deploy backend
    success, output = run_command("vercel --prod")
    if success:
        print("✅ Backend deployed successfully")
        # Extract URL from output
        lines = output.split('\n')
        for line in lines:
            if 'https://' in line and 'vercel.app' in line:
                backend_url = line.strip()
                print(f"📡 Backend URL: {backend_url}")
                return backend_url
    else:
        print("❌ Backend deployment failed")
        return None

def deploy_frontend(backend_url):
    """Deploy frontend to Vercel."""
    print("Deploying frontend to Vercel...")
    
    # Change to frontend directory
    frontend_dir = os.path.join(os.getcwd(), 'frontend')
    
    # Deploy frontend
    success, output = run_command("vercel --prod", cwd=frontend_dir)
    if success:
        print("✅ Frontend deployed successfully")
        # Extract URL from output
        lines = output.split('\n')
        for line in lines:
            if 'https://' in line and 'vercel.app' in line:
                frontend_url = line.strip()
                print(f"🌐 Frontend URL: {frontend_url}")
                return frontend_url
    else:
        print("❌ Frontend deployment failed")
        return None

def run_migrations(backend_url):
    """Run database migrations."""
    print("Running database migrations...")
    
    # Set environment variables for migrations
    env = os.environ.copy()
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings_prod'
    
    # Run migrations
    success, output = run_command("python migrate.py")
    if success:
        print("✅ Migrations completed")
    else:
        print("❌ Migrations failed")
        print(output)

def test_deployment(frontend_url, backend_url):
    """Test the deployment."""
    print("Testing deployment...")
    
    import requests
    
    # Test backend API
    try:
        response = requests.get(f"{backend_url}/api/v1/auth/registro/", timeout=10)
        if response.status_code == 405:  # Method not allowed is expected for GET on POST endpoint
            print("✅ Backend API responding")
        else:
            print(f"⚠️ Backend API status: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend API test failed: {e}")
    
    # Test frontend
    try:
        response = requests.get(frontend_url, timeout=10)
        if response.status_code == 200:
            print("✅ Frontend responding")
        else:
            print(f"⚠️ Frontend status: {response.status_code}")
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")

def main():
    """Main deployment function."""
    print("🚀 Starting Vercel + Supabase Deployment")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Prepare git
    if not prepare_git():
        sys.exit(1)
    
    # Deploy backend
    backend_url = deploy_backend()
    if not backend_url:
        sys.exit(1)
    
    # Deploy frontend
    frontend_url = deploy_frontend(backend_url)
    if not frontend_url:
        sys.exit(1)
    
    # Run migrations (this would need to be done manually or via Vercel cron)
    print("⚠️ Note: Database migrations need to be run manually in production")
    print("   Connect to your Supabase project and run the migrations")
    
    # Test deployment
    test_deployment(frontend_url, backend_url)
    
    print("\n" + "=" * 50)
    print("🎉 Deployment Complete!")
    print(f"🌐 Frontend: {frontend_url}")
    print(f"📡 Backend API: {backend_url}/api/v1/")
    print(f"📚 API Docs: {backend_url}/api/docs/")
    print("\n📝 Next Steps:")
    print("1. Set up Supabase database")
    print("2. Run migrations manually")
    print("3. Configure environment variables in Vercel")
    print("4. Test all functionality")

if __name__ == "__main__":
    main()
