#!/usr/bin/env python3
"""
Minecraft Mod Handler Web Application Launcher
"""

import os
import sys
import subprocess
import webbrowser
import time
import threading
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import flask
        import requests
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False

def check_ollama():
    """Check if Ollama is running"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama is running with {len(models)} models available")
            return True
        else:
            print("⚠️  Ollama is running but returned an error")
            return False
    except Exception as e:
        print(f"❌ Ollama is not running or not accessible: {e}")
        print("Please start Ollama: ollama serve")
        return False

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

def main():
    """Main launcher function"""
    print("🎮 Minecraft Mod Handler - Web Application")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        input("Press Enter to exit...")
        return
    
    # Check Ollama
    ollama_running = check_ollama()
    if not ollama_running:
        print("\n⚠️  Warning: Ollama is not running. AI features will not be available.")
        print("To start Ollama:")
        print("  1. Install Ollama from https://ollama.ai")
        print("  2. Run: ollama serve")
        print("  3. Pull a model: ollama pull llama3.2")
        print()
    
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🚀 Starting web application...")
    print("📱 The application will open in your browser automatically")
    print("🌐 Manual access: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Open browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # Import and run the Flask app
        from app import app
        print("🔄 Auto-reload enabled - server will restart automatically on file changes")
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down web application...")
    except Exception as e:
        print(f"\n❌ Error starting web application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
