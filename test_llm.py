"""
Test script for LLM API connectivity.
Run this script to verify your API key is working correctly.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_deepseek_api():
    """Test connection to DeepSeek API."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ ERROR: DeepSeek API key not found in .env file")
        print("Please add DEEPSEEK_API_KEY=your_api_key to your .env file")
        return False
    
    print(f"✓ Found DeepSeek API key: {api_key[:5]}...{api_key[-4:]}")
    
    # DeepSeek API endpoint
    api_url = "https://api.deepseek.com/v1/chat/completions"
    
    # Headers with authorization
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Simple test payload
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Say hello world"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    print("\nSending test request to DeepSeek API...")
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print("\n✅ SUCCESS! API response received:")
            print("-" * 50)
            print(content)
            print("-" * 50)
            return True
        else:
            print(f"\n❌ ERROR: API returned status code {response.status_code}")
            print("Response:")
            print(response.text)
            return False
    
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to DeepSeek API")
        print("Please check your internet connection and API URL")
        return False
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request to DeepSeek API timed out")
        print("The service might be overloaded or down")
        return False
    except json.JSONDecodeError:
        print("\n❌ ERROR: Could not parse API response as JSON")
        print(f"Raw response: {response.text}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

def show_env_instructions():
    """Display instructions for setting up the .env file."""
    print("\n" + "=" * 60)
    print("ENVIRONMENT SETUP INSTRUCTIONS")
    print("=" * 60)
    print("1. Create a file named '.env' in the same directory as this script")
    print("2. Add your DeepSeek API key to the file in this format:")
    print("\nDEEPSEEK_API_KEY=your_api_key_here\n")
    print("3. You can also add these optional settings:")
    print("LLM_API_URL=https://api.deepseek.com/v1/chat/completions")
    print("LLM_MODEL=deepseek-chat")
    print("=" * 60)

def main():
    """Main function to run the test."""
    print("🔍 LLM API Connection Test")
    print("-" * 30)
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("❌ ERROR: .env file not found")
        show_env_instructions()
        return
    
    # Test DeepSeek API
    success = test_deepseek_api()
    
    if success:
        print("\n✅ DeepSeek API is working correctly!")
        print("\nYou can now use the LLM features in your Jira app.")
        print("Make sure to restart your Flask app after setting up the API key.")
    else:
        print("\n❌ Error connecting to DeepSeek API")
        print("Please check your API key and try again.")
        show_env_instructions()

if __name__ == "__main__":
    main()