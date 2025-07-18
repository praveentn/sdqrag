# setup.py
import os
import sys
import subprocess
import json
import requests
from pathlib import Path
import argparse
from sentence_transformers import SentenceTransformer
import sqlite3

def print_header():
    """Print setup header"""
    print("=" * 60)
    print("         QueryForge - Enterprise RAG Platform")
    print("                    Setup Script")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    print("🔍 Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    directories = [
        'uploads',
        'models',
        'indexes',
        'logs',
        'backups'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   Created: {directory}/")
    
    print("✅ Directories created successfully")

def setup_environment():
    """Setup environment file"""
    print("⚙️  Setting up environment configuration...")
    
    env_template = """# QueryForge Environment Configuration

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production

# Database Configuration
DATABASE_URL=sqlite:///queryforge.db

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_MODEL=gpt-4

# File Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=104857600

# Application Configuration
DEBUG=True
PORT=5000
"""
    
    env_file = Path('.env')
    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(env_template)
        print("✅ Created .env file with default configuration")
        print("⚠️  Please update .env file with your Azure OpenAI credentials")
    else:
        print("✅ .env file already exists")

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        print("✅ Python dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)

def download_embedding_models(models=None):
    """Download specified embedding models"""
    if models is None:
        models = [
            'sentence-transformers/all-MiniLM-L6-v2',
            'sentence-transformers/all-mpnet-base-v2'
        ]
    
    print("🤖 Downloading embedding models...")
    models_dir = Path('models')
    
    for model_name in models:
        print(f"   Downloading {model_name}...")
        try:
            # Create model-specific directory
            model_dir = models_dir / model_name.replace('/', '_')
            model_dir.mkdir(exist_ok=True)
            
            # Download model
            model = SentenceTransformer(model_name, cache_folder=str(models_dir))
            
            # Save model locally
            local_path = model_dir / 'model'
            model.save(str(local_path))
            
            print(f"   ✅ {model_name} downloaded successfully")
            
        except Exception as e:
            print(f"   ❌ Error downloading {model_name}: {e}")
    
    print("✅ Embedding models setup completed")

def setup_database():
    """Initialize database"""
    print("🗄️  Setting up database...")
    
    try:
        # Import and setup database
        from app import app, db
        
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Create default admin user if not exists
            from models import User
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@queryforge.com',
                    role='admin',
                    is_active=True
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Default admin user created (username: admin, password: admin123)")
            else:
                print("✅ Admin user already exists")
                
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        sys.exit(1)

def install_npm_dependencies():
    """Install Node.js dependencies for React frontend"""
    print("📦 Installing Node.js dependencies...")
    
    try:
        # Check if npm is available
        subprocess.check_call(['npm', '--version'], stdout=subprocess.DEVNULL)
        
        # Install dependencies
        subprocess.check_call(['npm', 'install'], cwd='.')
        print("✅ Node.js dependencies installed successfully")
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  npm not found. Please install Node.js and npm manually")
        print("   Then run: npm install")

def build_frontend():
    """Build React frontend"""
    print("🏗️  Building React frontend...")
    
    try:
        subprocess.check_call(['npm', 'run', 'build'], cwd='.')
        print("✅ Frontend built successfully")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Could not build frontend. Please run 'npm run build' manually")

def test_azure_openai():
    """Test Azure OpenAI connection"""
    print("🧪 Testing Azure OpenAI connection...")
    
    try:
        from services.llm_service import LLMService
        
        llm_service = LLMService()
        if llm_service.is_available():
            test_result = llm_service.test_connection()
            if test_result['status'] == 'success':
                print("✅ Azure OpenAI connection successful")
            else:
                print(f"⚠️  Azure OpenAI test failed: {test_result['message']}")
        else:
            print("⚠️  Azure OpenAI not configured. Please update .env file")
            
    except Exception as e:
        print(f"⚠️  Could not test Azure OpenAI: {e}")

def create_sample_project():
    """Create a sample project for demonstration"""
    print("📋 Creating sample project...")
    
    try:
        from app import app, db
        from models import Project, User
        
        with app.app_context():
            # Get admin user
            admin_user = User.query.filter_by(username='admin').first()
            
            # Check if sample project exists
            sample_project = Project.query.filter_by(name='Sample Project').first()
            
            if not sample_project:
                sample_project = Project(
                    name='Sample Project',
                    description='A sample project to demonstrate QueryForge capabilities',
                    created_by=admin_user.id
                )
                db.session.add(sample_project)
                db.session.commit()
                print("✅ Sample project created")
            else:
                print("✅ Sample project already exists")
                
    except Exception as e:
        print(f"⚠️  Could not create sample project: {e}")

def print_completion_message():
    """Print setup completion message"""
    print()
    print("=" * 60)
    print("🎉 QueryForge setup completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Update the .env file with your Azure OpenAI credentials")
    print("2. Start the application:")
    print("   python app.py")
    print()
    print("3. Access the application at: http://localhost:5000")
    print()
    print("Default login credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print()
    print("For production deployment:")
    print("- Change the SECRET_KEY in .env")
    print("- Change the default admin password")
    print("- Use a production database (PostgreSQL)")
    print("- Set FLASK_ENV=production")
    print()

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description='QueryForge Setup Script')
    parser.add_argument('--skip-models', action='store_true', 
                       help='Skip downloading embedding models')
    parser.add_argument('--skip-frontend', action='store_true',
                       help='Skip frontend build')
    parser.add_argument('--models', nargs='+', 
                       help='Specific models to download')
    
    args = parser.parse_args()
    
    print_header()
    
    try:
        check_python_version()
        create_directories()
        setup_environment()
        # install_dependencies()
        
        if not args.skip_models:
            download_embedding_models(args.models)
        
        setup_database()
        
        # if not args.skip_frontend:
        #     install_npm_dependencies()
        #     build_frontend()
        
        test_azure_openai()
        create_sample_project()
        
        print_completion_message()
        
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()