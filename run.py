# run.py
import os
import sys
import subprocess
import time
import argparse
from pathlib import Path

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("         QueryForge - Enterprise RAG Platform")
    print("=" * 60)
    print()

def check_requirements():
    """Check if all requirements are installed"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        return False
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ Error: .env file not found. Please run setup.py first")
        return False
    
    # Check if required packages are installed
    try:
        import flask
        import sqlalchemy
        import sentence_transformers
        print("✅ Python dependencies are installed")
    except ImportError as e:
        print(f"❌ Error: Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    # Check if build directory exists (for production)
    if not os.path.exists('build') and not args.dev:
        print("⚠️  Warning: React build not found. Running in development mode")
        return True
    
    return True

def start_development():
    """Start application in development mode"""
    print("🚀 Starting QueryForge in development mode...")
    
    # Start Flask backend
    env = os.environ.copy()
    env['FLASK_ENV'] = 'development'
    env['DEBUG'] = 'True'
    
    try:
        subprocess.run([
            sys.executable, 'app.py'
        ], env=env)
    except KeyboardInterrupt:
        print("\n👋 QueryForge stopped")

def start_production():
    """Start application in production mode"""
    print("🚀 Starting QueryForge in production mode...")
    
    # Check if gunicorn is available
    try:
        import gunicorn
    except ImportError:
        print("❌ Error: gunicorn not installed. Installing...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'gunicorn'])
    
    # Start with gunicorn
    env = os.environ.copy()
    env['FLASK_ENV'] = 'production'
    
    try:
        subprocess.run([
            'gunicorn',
            '-w', '4',
            '-b', '0.0.0.0:5000',
            '--timeout', '120',
            '--keep-alive', '5',
            'app:app'
        ], env=env)
    except KeyboardInterrupt:
        print("\n👋 QueryForge stopped")

def health_check():
    """Perform health check"""
    print("🏥 Performing health check...")
    
    import requests
    import time
    
    # Wait a moment for the server to start
    time.sleep(2)
    
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Application is healthy")
            print(f"   Status: {data.get('status')}")
            print(f"   Database: {data.get('database')}")
            print(f"   Version: {data.get('version')}")
            return True
        else:
            print(f"⚠️  Health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Health check failed: {e}")
        return False

def setup_check():
    """Check if initial setup is complete"""
    print("🔧 Checking setup status...")
    
    # Check database
    if os.path.exists('queryforge.db'):
        print("✅ Database exists")
    else:
        print("⚠️  Database not found. Running initial setup...")
        try:
            from app import app, db
            with app.app_context():
                db.create_all()
            print("✅ Database initialized")
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False
    
    # Check if embedding models directory exists
    if os.path.exists('models'):
        model_count = len(list(Path('models').rglob('*.bin')))
        if model_count > 0:
            print(f"✅ Found {model_count} embedding model files")
        else:
            print("⚠️  No embedding models found. You may want to download them:")
            print("   python setup.py --models")
    else:
        print("ℹ️  No models directory found. Models will be downloaded as needed.")
    
    return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='QueryForge Application Launcher')
    parser.add_argument('--dev', action='store_true', help='Run in development mode')
    parser.add_argument('--prod', action='store_true', help='Run in production mode')
    parser.add_argument('--check', action='store_true', help='Run health check only')
    parser.add_argument('--setup', action='store_true', help='Run setup check only')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    
    global args
    args = parser.parse_args()
    
    print_banner()
    
    # Setup check
    if args.setup:
        setup_check()
        return
    
    # Health check only
    if args.check:
        health_check()
        return
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Setup check
    if not setup_check():
        print("❌ Setup check failed. Please run setup.py first")
        sys.exit(1)
    
    # Set port
    os.environ['PORT'] = str(args.port)
    
    # Determine run mode
    if args.prod:
        start_production()
    elif args.dev:
        start_development()
    else:
        # Auto-detect based on environment
        flask_env = os.environ.get('FLASK_ENV', 'development')
        if flask_env == 'production':
            start_production()
        else:
            start_development()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)