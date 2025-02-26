# ultra_simple_test.py
import os
import requests
from dotenv import load_dotenv

# Add explicit error handling
try:
    print("Starting ultra simple test...")
    
    # Load .env file
    print("Loading environment variables...")
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: No DEEPSEEK_API_KEY found in .env file")
        exit(1)
    else:
        print(f"Found API key: {api_key[:5]}...{api_key[-4:]}")
    
    # Test Jira connection
    print("\nTesting Jira connection...")
    jira_url = "http://localhost:8080"
    pat = os.getenv("PAT")
    
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }
    
    jira_test_url = f"{jira_url}/rest/api/2/serverInfo"
    print(f"Requesting: {jira_test_url}")
    
    jira_response = requests.get(jira_test_url, headers=headers, timeout=10)
    print(f"Jira response code: {jira_response.status_code}")
    
    if jira_response.status_code == 200:
        print("✅ Jira connection successful")
    else:
        print(f"❌ Jira connection failed: {jira_response.text[:100]}")
    
    # Test LLM connection
    print("\nTesting LLM connection...")
    llm_url = "https://api.deepseek.com/v1/chat/completions"
    llm_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    llm_payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Say hello"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    print(f"Sending request to: {llm_url}")
    llm_response = requests.post(llm_url, headers=llm_headers, json=llm_payload, timeout=30)
    print(f"LLM response code: {llm_response.status_code}")
    
    if llm_response.status_code == 200:
        result = llm_response.json()
        content = result["choices"][0]["message"]["content"]
        print("✅ LLM connection successful")
        print(f"Response: {content}")
    else:
        print(f"❌ LLM connection failed: {llm_response.text[:100]}")
    
    print("\nTest completed successfully.")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    print(traceback.format_exc())