import requests

# Jira configuration
JIRA_URL = "http://localhost:8080"
#PAT = "jira api token"
PROJECT_KEY = "DEMO"

# Set up headers for authentication
headers = {
    "Authorization": f"Bearer {PAT}",
    "Content-Type": "application/json"
}

# JQL query to get the latest 10 issues from the DEMO project
jql = f"project = {PROJECT_KEY} order by created DESC"
api_url = f"{JIRA_URL}/rest/api/2/search?jql={jql}&maxResults=10"

# Make the GET request to Jira
try:
    response = requests.get(api_url, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        issues = response.json()["issues"]
        print("Latest Tickets from Jira (Project: DEMO):")
        for issue in issues:
            key = issue["key"]
            summary = issue["fields"]["summary"]
            print(f"- {key}: {summary}")
    else:
        print(f"Error: Received status code {response.status_code}. Message: {response.text}")
except Exception as e:
    print(f"Something went wrong: {e}")
