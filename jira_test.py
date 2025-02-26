# jira_test.py
import requests
import json

# Jira settings
JIRA_URL = "http://localhost:8080"
pat = os.getenv("PAT")

def get_auth_headers(pat):
    return {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

print("Testing Jira connection...")
# Test with server info endpoint
url = f"{JIRA_URL}/rest/api/2/serverInfo"
print(f"Requesting: {url}")

try:
    response = requests.get(url, headers=get_auth_headers(PAT), timeout=10)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Jira connection successful!")
        server_info = response.json()
        print(f"Base URL: {server_info.get('baseUrl')}")
        print(f"Version: {server_info.get('version')}")
        
        # Now check if any projects exist
        projects_url = f"{JIRA_URL}/rest/api/2/project"
        print(f"\nRequesting projects: {projects_url}")
        projects_response = requests.get(projects_url, headers=get_auth_headers(PAT), timeout=10)
        
        if projects_response.status_code == 200:
            projects = projects_response.json()
            print(f"Found {len(projects)} projects:")
            for project in projects:
                print(f"- {project.get('key')}: {project.get('name')}")
                
            # Get tickets from the first project
            if projects:
                project_key = projects[0].get('key')
                print(f"\nFetching tickets for project {project_key}...")
                
                jql = f"project = {project_key} ORDER BY created DESC"
                tickets_url = f"{JIRA_URL}/rest/api/2/search?jql={jql}&maxResults=5"
                
                tickets_response = requests.get(tickets_url, headers=get_auth_headers(PAT), timeout=10)
                
                if tickets_response.status_code == 200:
                    tickets_data = tickets_response.json()
                    tickets = tickets_data.get('issues', [])
                    
                    print(f"Found {len(tickets)} tickets:")
                    for ticket in tickets:
                        key = ticket.get('key')
                        summary = ticket.get('fields', {}).get('summary', 'No summary')
                        print(f"- {key}: {summary}")
                else:
                    print(f"❌ Failed to fetch tickets: {tickets_response.status_code}")
        else:
            print(f"❌ Failed to fetch projects: {projects_response.status_code}")
    else:
        print(f"❌ Jira connection failed: {response.text}")
except Exception as e:
    print(f"❌ Exception: {str(e)}")