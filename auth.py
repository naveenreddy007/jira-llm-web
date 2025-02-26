import requests

def get_jira_details():
    """Prompt user for Jira details."""
    jira_url = input("Enter Jira URL (e.g., http://localhost:8080): ").strip()
    pat = input("Enter your Jira Personal Access Token (PAT): ").strip()

    return jira_url, pat

def get_auth_headers(pat):
    """Return headers for authentication."""
    return {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

def test_jira_connection(jira_url, pat):
    """Test connection to Jira by checking server info."""
    test_url = f"{jira_url}/rest/api/2/serverInfo"
    
    try:
        response = requests.get(test_url, headers=get_auth_headers(pat), timeout=10)
        
        if response.status_code == 200:
            print("✅ Connected to Jira successfully!")
            return True
        else:
            print(f"❌ Connection failed: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Jira Authentication Setup")
    
    jira_url, pat = get_jira_details()
    
    print("\n🔄 Testing connection...")
    if test_jira_connection(jira_url, pat):
        print("✅ Jira is ready to use!")
    else:
        print("❌ Please check your details and try again.")
