#!/usr/bin/env python3
"""
Startup script for Private Document Q&A System.
This script provides an easy way to start the application with proper configuration.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'flask',
        'llama_index',
        'openai',
        'chromadb',
        'loguru'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nPlease install missing packages with:")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def check_environment():
    """Check if environment is properly configured."""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set up your environment variables:")
        print("1. Copy env.example to .env")
        print("2. Edit .env with your configuration")
        print("3. Set your OpenAI API key")
        return False
    
    print("✅ Environment variables are configured")
    return True

def create_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        'documents',
        'index',
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directories created/verified")

def main():
    """Main startup function."""
    print("🚀 Starting Private Document Q&A System")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    print("\n✅ System ready to start!")
    print("\nStarting application...")
    print("=" * 50)
    
    # Import and run the application
    try:
        from app import main as app_main
        app_main()
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 