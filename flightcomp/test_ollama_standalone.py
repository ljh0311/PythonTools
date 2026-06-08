#!/usr/bin/env python3
"""
Standalone Ollama Test Script
Run this script independently to test Ollama integration without the full application
"""

import sys
import os
import requests
import json

def test_ollama_connection():
    """Test basic Ollama connection"""
    print("🔍 Testing Ollama connection...")
    
    try:
        # Test basic connection
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code == 200:
            print("✅ Ollama connection successful!")
            
            # Get available models
            models_data = response.json()
            models = models_data.get("models", [])
            
            if models:
                model_names = [model["name"] for model in models]
                print(f"📦 Available models: {', '.join(model_names)}")
                return True, model_names
            else:
                print("⚠️  No models found. Please install a model with 'ollama pull llama2'")
                return False, []
        else:
            print(f"❌ Ollama API returned status code {response.status_code}")
            return False, []
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama. Is it running?")
        print("   Start Ollama with: ollama serve")
        return False, []
    except requests.exceptions.Timeout:
        print("❌ Connection timeout. Ollama may be starting up.")
        return False, []
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, []

def test_model_generation(model_name="llama2"):
    """Test model generation"""
    print(f"\n🧪 Testing model generation with {model_name}...")
    
    try:
        # Simple test prompt
        payload = {
            "model": model_name,
            "prompt": "Hello, how are you?",
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 50
            }
        }
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "").strip()
            
            if generated_text:
                print(f"✅ Generation successful!")
                print(f"📝 Response: {generated_text}")
                return True
            else:
                print("⚠️  Empty response from model")
                return False
        else:
            print(f"❌ Generation failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Generation error: {e}")
        return False

def test_atc_response():
    """Test ATC response generation"""
    print(f"\n✈️  Testing ATC response generation...")
    
    try:
        # ATC-style prompt
        payload = {
            "model": "llama2",
            "prompt": """You are an Air Traffic Controller. Respond to this pilot message:

PILOT: "Request taxi clearance to runway 27"

Respond with ONLY the ATC instruction, no explanations:""",
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 100,
                "stop": ["\n\n", "PILOT:", "ATC:"]
            }
        }
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "").strip()
            
            if generated_text:
                print(f"✅ ATC response generated!")
                print(f"🎯 Response: {generated_text}")
                return True
            else:
                print("⚠️  Empty ATC response")
                return False
        else:
            print(f"❌ ATC generation failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ ATC generation error: {e}")
        return False

def show_setup_instructions():
    """Show setup instructions"""
    print("\n📋 SETUP INSTRUCTIONS:")
    print("=" * 50)
    print("1. Install Ollama:")
    print("   • Windows: Download from https://ollama.ai")
    print("   • macOS: brew install ollama")
    print("   • Linux: curl -fsSL https://ollama.ai/install.sh | sh")
    print()
    print("2. Start Ollama service:")
    print("   ollama serve")
    print()
    print("3. Download a model:")
    print("   ollama pull llama2")
    print("   # or for faster performance:")
    print("   ollama pull llama2:7b")
    print()
    print("4. Test the model:")
    print("   ollama run llama2 'Hello'")
    print()
    print("5. Run this test script again")
    print("=" * 50)

def main():
    """Main test function"""
    print("🚁 Ollama AI Integration Test")
    print("=" * 50)
    
    # Test connection
    connection_ok, models = test_ollama_connection()
    
    if not connection_ok:
        show_setup_instructions()
        return 1
    
    # Test generation if we have models
    if models:
        # Test with first available model
        model_name = models[0]
        generation_ok = test_model_generation(model_name)
        
        if generation_ok:
            # Test ATC response
            atc_ok = test_atc_response()
            
            if atc_ok:
                print("\n" + "=" * 50)
                print("🎉 All tests passed! Ollama is working correctly.")
                print("=" * 50)
                print("\nYou can now use AI features in the Aviation Assistant:")
                print("1. Launch the application")
                print("2. Select 'ATC' role")
                print("3. Use AI response features in Ground Control")
                return 0
            else:
                print("\n❌ ATC response test failed")
                return 1
        else:
            print("\n❌ Model generation test failed")
            return 1
    else:
        print("\n❌ No models available")
        show_setup_instructions()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
