#!/usr/bin/env python3
"""
Test script for Ollama integration
Run this script to test if Ollama is working correctly
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ollama_connection():
    """Test basic Ollama connection"""
    print("Testing Ollama connection...")
    
    try:
        from utils.ollama_client import OllamaClient
        
        # Test connection
        client = OllamaClient()
        
        if client.is_available():
            print("✅ Ollama connection successful!")
            
            # Test model availability
            models = client.get_available_models()
            if models:
                print(f"✅ Available models: {', '.join(models)}")
            else:
                print("⚠️  No models found. Please install a model with 'ollama pull llama2'")
                return False
                
            # Test simple response generation
            print("Testing response generation...")
            test_response = client.generate_atc_response(
                pilot_message="Request taxi clearance to runway 27",
                aircraft_info={
                    'callsign': 'TEST123',
                    'aircraft_type': 'C172',
                    'location': 'Gate A1',
                    'status': 'Ready',
                    'squawk_code': '1200'
                },
                airport_info={
                    'name': 'Test Airport',
                    'icao': 'TEST',
                    'runways': ['27', '09'],
                    'taxiways': ['A', 'B', 'C'],
                    'wind': '220° at 10kts',
                    'visibility': '10 miles'
                }
            )
            
            print(f"✅ Test response: {test_response}")
            return True
            
        else:
            print("❌ Ollama connection failed!")
            print("Please make sure Ollama is running with 'ollama serve'")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install required dependencies with 'pip install -r requirements.txt'")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_ai_handler():
    """Test AI response handler"""
    print("\nTesting AI response handler...")
    
    try:
        from utils.ai_response_handler import AIResponseHandler
        
        # Test configuration
        config = {
            'ai_enabled': True,
            'ai_model': 'llama2',
            'ollama_url': 'http://localhost:11434',
            'ai_temperature': 0.7
        }
        
        handler = AIResponseHandler(config)
        
        if handler.is_ai_available():
            print("✅ AI handler initialized successfully!")
            
            # Test response generation
            response = handler.generate_atc_response(
                pilot_message="Ready for departure",
                aircraft_info={
                    'callsign': 'TEST456',
                    'aircraft_type': 'B737',
                    'location': 'Runway 27',
                    'status': 'Ready',
                    'squawk_code': '1200'
                },
                airport_info={
                    'name': 'Test Airport',
                    'icao': 'TEST',
                    'runways': ['27', '09'],
                    'taxiways': ['A', 'B', 'C'],
                    'wind': '220° at 10kts',
                    'visibility': '10 miles'
                }
            )
            
            print(f"✅ AI handler response: {response}")
            return True
        else:
            print("❌ AI handler not available")
            return False
            
    except Exception as e:
        print(f"❌ AI handler error: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 50)
    print("Ollama Integration Test")
    print("=" * 50)
    
    # Test basic connection
    connection_ok = test_ollama_connection()
    
    if connection_ok:
        # Test AI handler
        handler_ok = test_ai_handler()
        
        if handler_ok:
            print("\n" + "=" * 50)
            print("✅ All tests passed! Ollama integration is working correctly.")
            print("=" * 50)
            print("\nYou can now use the AI features in the Aviation Assistant:")
            print("1. Launch the application")
            print("2. Select 'ATC' role")
            print("3. Click 'AI Settings' to configure")
            print("4. Use the AI response features in Ground Control")
        else:
            print("\n❌ AI handler test failed")
            sys.exit(1)
    else:
        print("\n❌ Connection test failed")
        print("\nTroubleshooting steps:")
        print("1. Install Ollama: https://ollama.ai")
        print("2. Start Ollama: ollama serve")
        print("3. Install a model: ollama pull llama2")
        print("4. Run this test again")
        sys.exit(1)

if __name__ == "__main__":
    main()
