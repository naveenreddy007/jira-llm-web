# fixed_llm_chat.py
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a minimal Flask app for testing
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# Create a simple LLM service for testing
class SimpleLLMService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("No DEEPSEEK_API_KEY found in environment")
    
    def generate_response(self, prompt, system_prompt=None):
        # API details
        api_url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Create messages array
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Create payload
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Make the API call
        print(f"SENDING TO API: {prompt[:100]}...")
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"API Error: {response.status_code} - {response.text}"

# Initialize LLM service
llm_service = SimpleLLMService()

def get_auth_headers(pat):
    """Return headers for Jira authentication."""
    return {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

@app.route("/fixed_chat", methods=["GET", "POST"])
def fixed_chat():
    """A fixed chat interface that works correctly with the LLM."""
    response = None
    question = None
    debug_info = {}
    
    if request.method == "POST":
        # Get the question from the form
        question = request.form.get("question", "")
        print(f"Question received: '{question}'")
        
        # Always try to get tickets from Jira
        jira_url = "http://localhost:8080"  # Hardcoded for testing
        pat = os.getenv("PAT")
        
        jira_data = []
        tickets_text = ""
        
        # Try to get any tickets, not just high priority
        try:
            jql = "ORDER BY created DESC"  # This will get any tickets
            search_url = f"{jira_url}/rest/api/2/search?jql={jql}&maxResults=5"
            
            print(f"Fetching tickets from: {search_url}")
            resp = requests.get(search_url, headers=get_auth_headers(pat), timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                jira_data = data.get("issues", [])
                print(f"Found {len(jira_data)} tickets")
                
                # Create text representation of tickets
                if jira_data:
                    tickets_text = "Here are some recent Jira tickets:\n\n"
                    for issue in jira_data:
                        key = issue["key"]
                        summary = issue["fields"]["summary"]
                        status = issue["fields"]["status"]["name"]
                        tickets_text += f"- {key}: {summary} (Status: {status})\n"
            else:
                print(f"Error fetching tickets: {resp.status_code} - {resp.text[:100]}")
        except Exception as e:
            print(f"Exception fetching tickets: {str(e)}")
        
        # Create the complete prompt
        complete_prompt = f"User question: {question}\n\n"
        if tickets_text:
            complete_prompt += tickets_text
        
        # Save debug info
        debug_info = {
            "question": question,
            "question_length": len(question),
            "tickets_found": len(jira_data),
            "prompt_length": len(complete_prompt),
            "tickets_text_length": len(tickets_text),
            "prompt_preview": complete_prompt[:100] + "..." if len(complete_prompt) > 100 else complete_prompt
        }
        
        # Send to LLM
        try:
            system_prompt = "You are a helpful Jira assistant. Answer the user's question based on the Jira ticket data if provided."
            response = llm_service.generate_response(
                prompt=complete_prompt,
                system_prompt=system_prompt
            )
        except Exception as e:
            response = f"Error: {str(e)}"
    
    # Render a simple HTML page
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fixed LLM Chat</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container mt-5">
            <h1>Fixed LLM Chat</h1>
            
            <div class="card mt-4">
                <div class="card-body">
                    <!-- Replace your entire form with this simpler version -->

<form method="POST" action="{{ url_for('llm_chat') }}">
  <div class="input-group">
    <input type="text" class="form-control" name="question" placeholder="Ask a question..." required>
    <button class="btn btn-primary" type="submit">
      Send
    </button>
  </div>
  
  <div class="mt-3">
    <p class="text-muted">Suggested questions:</p>
    <div class="d-flex flex-wrap gap-2">
      <button type="button" class="btn btn-sm btn-outline-secondary suggestion-btn" 
              onclick="document.querySelector('input[name=question]').value=this.innerText;document.querySelector('form').submit();">
        What are my highest priority tickets?
      </button>
      <button type="button" class="btn btn-sm btn-outline-secondary suggestion-btn"
              onclick="document.querySelector('input[name=question]').value=this.innerText;document.querySelector('form').submit();">
        Summarize the DEMO project status
      </button>
      <button type="button" class="btn btn-sm btn-outline-secondary suggestion-btn"
              onclick="document.querySelector('input[name=question]').value=this.innerText;document.querySelector('form').submit();">
        What tickets are assigned to me?
      </button>
      <button type="button" class="btn btn-sm btn-outline-secondary suggestion-btn"
              onclick="document.querySelector('input[name=question]').value=this.innerText;document.querySelector('form').submit();">
        Find tickets due this week
      </button>
    </div>
  </div>
</form>

<!-- No JavaScript needed with this approach! -->
                </div>
            </div>
            
            {f'''
            <div class="card mt-4">
                <div class="card-header">Your Question</div>
                <div class="card-body">
                    <p>{question}</p>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">LLM Response</div>
                <div class="card-body">
                    <p>{response}</p>
                </div>
            </div>
            ''' if response else ''}
            
            <div class="card mt-4">
                <div class="card-header">Debug Information</div>
                <div class="card-body">
                    <pre>{str(debug_info)}</pre>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

if __name__ == "__main__":
    # Run the standalone app for testing
    print("Starting standalone LLM chat test app...")
    app.run(debug=True, port=5001)  # Use a different port than the main app