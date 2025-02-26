# debug_test.py
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Jira settings
JIRA_URL = "http://localhost:8080"
pat = os.getenv("PAT")
# LLM settings
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def test_jira_connection():
    """Test connection to Jira."""
    print("Testing Jira connection...")
    headers = {
        "Authorization": f"Bearer {PAT}",
        "Content-Type": "application/json"
    }
    
    try:
        # Test with server info endpoint
        url = f"{JIRA_URL}/rest/api/2/serverInfo"
        print(f"Requesting: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Response code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Connected to Jira successfully!")
            print(f"Response: {json.dumps(response.json(), indent=2)[:200]}...")
            return True
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def get_high_priority_tickets():
    """Get high priority tickets from Jira."""
    print("\nFetching high priority tickets...")
    headers = {
        "Authorization": f"Bearer {PAT}",
        "Content-Type": "application/json"
    }
    
    try:
        # Create JQL query for high priority tickets
        jql = "priority = Highest OR priority = High ORDER BY created DESC"
        url = f"{JIRA_URL}/rest/api/2/search?jql={jql}&maxResults=5"
        
        print(f"Requesting: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Response code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            issues = data.get("issues", [])
            print(f"✅ Found {len(issues)} high priority tickets")
            
            # Print ticket details
            for issue in issues:
                key = issue["key"]
                summary = issue["fields"]["summary"]
                priority = issue["fields"].get("priority", {}).get("name", "Unknown")
                print(f"- {key}: {summary} (Priority: {priority})")
            
            return issues
        else:
            print(f"❌ Failed to fetch tickets: {response.status_code}")
            print(f"Error: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return []

def test_llm_with_jira_data(tickets):
    """Test sending Jira data to LLM."""
    print("\nTesting LLM with Jira data...")
    
    if not DEEPSEEK_API_KEY:
        print("❌ DeepSeek API key not found")
        return
    
    # Format ticket data for prompt
    prompt = "Here are some high priority Jira tickets:\n\n"
    for issue in tickets:
        key = issue["key"]
        summary = issue["fields"]["summary"]
        priority = issue["fields"].get("priority", {}).get("name", "Unknown")
        prompt += f"- {key}: {summary} (Priority: {priority})\n"
    
    prompt += "\nPlease summarize these tickets and recommend which one should be addressed first."
    
    print(f"Sending prompt to LLM (length: {len(prompt)} chars)")
    print(f"First 200 chars of prompt: {prompt[:200]}...")
    
    # Send to DeepSeek API
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"Response code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print("\n✅ LLM response:")
            print("-" * 50)
            print(content)
            print("-" * 50)
        else:
            print(f"❌ LLM API error: {response.status_code}")
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

# Run the tests
if __name__ == "__main__":
    print("=" * 50)
    print("JIRA-LLM INTEGRATION TEST")
    print("=" * 50)
    
    # Test Jira connection
    if test_jira_connection():
        # If Jira is working, get tickets
        tickets = get_high_priority_tickets()
        
        if tickets:
            # If we have tickets, test LLM with them
            test_llm_with_jira_data(tickets)
    
    print("\nTest completed.")