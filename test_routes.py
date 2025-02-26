# test_routes.py
import requests

BASE_URL = "http://127.0.0.1:5000"
routes = [
    "/",  # Login page
    "/dashboard",  # Should redirect to login
    "/diagnostics",
    "/llm_dashboard",
    "/llm_chat",
    "/llm_status"
]

print("Testing all routes...")
print("-" * 50)

for route in routes:
    url = BASE_URL + route
    print(f"Testing {url}...")
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)} bytes")
        if response.status_code != 200:
            print(f"ERROR: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
    print("-" * 50)

print("Tests completed.")