from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import requests
import os
import logging
import traceback
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load the updated LLM service
try:
    from llm_service import get_llm_service, summarize_ticket, categorize_ticket, generate_response_suggestion, analyze_project_tickets
    llm_module_imported = True
except ImportError as e:
    print(f"WARNING: Error importing llm_service module: {e}")
    llm_module_imported = False

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # Get from env or use default
app.config["SESSION_TYPE"] = "filesystem"

# Initialize LLM service with better error handling
llm_service = None
if llm_module_imported:
    try:
        llm_service = get_llm_service()
        print("INFO: LLM service initialized successfully")
        # Test the connection immediately
        test_response = llm_service.generate_response("Test connection")
        print(f"INFO: LLM test response: {test_response[:50]}...")
    except Exception as e:
        print(f"WARNING: Failed to initialize LLM service: {str(e)}")
        print("Check your DEEPSEEK_API_KEY in .env file and ensure it's valid")

def get_auth_headers(pat):
    """Return headers for Jira authentication."""
    return {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

def test_jira_connection(jira_url, pat):
    """Test the connection by hitting the server info endpoint."""
    test_url = f"{jira_url}/rest/api/2/serverInfo"
    try:
        response = requests.get(test_url, headers=get_auth_headers(pat), timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def fetch_all_projects(jira_url, pat):
    """Fetch all Jira projects."""
    projects_url = f"{jira_url}/rest/api/2/project"
    try:
        response = requests.get(projects_url, headers=get_auth_headers(pat), timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            flash(f"Error fetching projects: {response.status_code}", "danger")
            return []
    except Exception as e:
        flash(f"Exception fetching projects: {e}", "danger")
        return []

def fetch_project_tickets(jira_url, pat, project_key, max_results=50):
    """Fetch tickets for a specific project."""
    jql = f"project = {project_key} ORDER BY created DESC"
    search_url = f"{jira_url}/rest/api/2/search?jql={jql}&maxResults={max_results}"
    
    try:
        response = requests.get(search_url, headers=get_auth_headers(pat), timeout=10)
        if response.status_code == 200:
            return response.json()["issues"]
        else:
            return []
    except Exception:
        return []

def get_ticket_details(jira_url, pat, ticket_key):
    """Fetch detailed information about a specific ticket."""
    issue_url = f"{jira_url}/rest/api/2/issue/{ticket_key}"
    
    try:
        response = requests.get(issue_url, headers=get_auth_headers(pat), timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
        return None

@app.route("/", methods=["GET", "POST"])
def login():
    """Login page for Jira authentication."""
    if request.method == "POST":
        jira_url = request.form["jira_url"].strip()
        pat = request.form["pat"].strip()
        
        if test_jira_connection(jira_url, pat):
            session["jira_url"] = jira_url
            session["pat"] = pat
            flash("✅ Connected to Jira successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Connection failed! Check your Jira details.", "danger")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    """Dashboard that fetches and displays all Jira projects."""
    if "jira_url" not in session or "pat" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("login"))
    
    jira_url = session["jira_url"]
    pat = session["pat"]
    projects = fetch_all_projects(jira_url, pat)
    
    # Pass LLM availability status to the template
    return render_template("dashboard.html", 
                          projects=projects, 
                          jira_url=jira_url,
                          llm_available=llm_service is not None)

@app.route("/logout")
def logout():
    """Log out and clear the session."""
    session.clear()
    flash("🔒 Logged out successfully!", "info")
    return redirect(url_for("login"))

# LLM Integration Routes

@app.route("/llm_dashboard")
def llm_dashboard():
    """Dashboard for LLM-powered features."""
    if "jira_url" not in session or "pat" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("login"))
    
    # Check if LLM service is available
    if llm_service is None:
        flash("⚠️ LLM service is not configured. Please check your API keys and the console for error messages.", "warning")
    
    jira_url = session["jira_url"]
    pat = session["pat"]
    projects = fetch_all_projects(jira_url, pat)
    
    return render_template("llm_dashboard.html", 
                          projects=projects, 
                          llm_available=llm_service is not None)

@app.route("/project/<project_key>/tickets")
def project_tickets(project_key):
    """View tickets for a specific project."""
    if "jira_url" not in session or "pat" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("login"))
    
    jira_url = session["jira_url"]
    pat = session["pat"]
    
    tickets = fetch_project_tickets(jira_url, pat, project_key)
    
    return render_template("project_tickets.html", 
                          tickets=tickets, 
                          project_key=project_key,
                          jira_url=jira_url,
                          llm_available=llm_service is not None)

@app.route("/ticket/<ticket_key>/analyze", methods=["GET"])
def analyze_ticket(ticket_key):
    """Analyze a ticket using LLM."""
    if "jira_url" not in session or "pat" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    if llm_service is None:
        return jsonify({
            "error": "LLM service not available",
            "summary": "LLM service is not configured. Please check your API keys and server logs.",
            "category": "N/A",
            "response_suggestion": "Unable to generate response without LLM service."
        }), 200  # Return 200 so the UI can display the error message
    
    jira_url = session["jira_url"]
    pat = session["pat"]
    
    ticket_data = get_ticket_details(jira_url, pat, ticket_key)
    if not ticket_data:
        return jsonify({"error": "Failed to fetch ticket details"}), 404
    
    try:
        # Extract relevant ticket information for LLM
        # Extract relevant ticket information for LLM
        fields = ticket_data["fields"]
        ticket_info = {
            "summary": fields.get("summary", ""),
            "description": fields.get("description", ""),
            "status": fields.get("status", {}).get("name", ""),
            "priority": fields.get("priority", {}).get("name", ""),
            "reporter": fields.get("reporter", {}).get("displayName", "")
        }
        
        # Generate LLM analysis
        summary = summarize_ticket(llm_service, ticket_info)
        category = categorize_ticket(llm_service, ticket_info)
        response = generate_response_suggestion(llm_service, ticket_info)
        
        return jsonify({
            "summary": summary,
            "category": category,
            "response_suggestion": response
        })
    except Exception as e:
        print(f"ERROR in analyze_ticket: {e}")
        return jsonify({
            "error": f"Error during analysis: {str(e)}",
            "summary": "An error occurred during analysis.",
            "category": "Error",
            "response_suggestion": f"Could not generate a response due to an error: {str(e)}"
        }), 200  # Return 200 so the UI can display the error

@app.route("/llm_chat", methods=["GET", "POST"])
def llm_chat():
    """Chat interface for asking questions about Jira data."""
    if "jira_url" not in session or "pat" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("login"))
    
    if llm_service is None:
        flash("⚠️ LLM service is not configured. Please check your API keys and server logs.", "warning")
        return redirect(url_for("dashboard"))
    
    response = None
    question = None
    jira_data = []
    debug_info = {}
    
    if request.method == "POST":
        question = request.form.get("question", "")
        jira_url = session["jira_url"]
        pat = session["pat"]
        
        print(f"Processing question: '{question}'")
        
        # First, try to get all projects
        projects = []
        try:
            projects_url = f"{jira_url}/rest/api/2/project"
            projects_response = requests.get(projects_url, headers=get_auth_headers(pat), timeout=10)
            
            if projects_response.status_code == 200:
                projects = projects_response.json()
                print(f"Found {len(projects)} projects")
        except Exception as e:
            print(f"Error fetching projects: {str(e)}")
        
        # If we have projects, try to get tickets from the first one
        project_key = None
        if projects:
            project_key = projects[0].get('key')
            print(f"Using project key: {project_key}")
        else:
            # Default to DEMO if no projects found
            project_key = "DEMO"
            print(f"No projects found, defaulting to {project_key}")
        
        # Try to get tickets using any valid JQL
        try:
            # Simple JQL to get recent tickets
            jql = f"project = {project_key} ORDER BY created DESC"
            search_url = f"{jira_url}/rest/api/2/search?jql={jql}&maxResults=5"
            
            print(f"Fetching tickets with URL: {search_url}")
            response = requests.get(search_url, headers=get_auth_headers(pat), timeout=10)
            
            if response.status_code == 200:
                results = response.json()
                jira_data = results.get("issues", [])
                print(f"Found {len(jira_data)} tickets")
            else:
                print(f"Error fetching tickets: {response.status_code}")
                # Try without project filter as fallback
                jql = "ORDER BY created DESC"
                search_url = f"{jira_url}/rest/api/2/search?jql={jql}&maxResults=5"
                
                print(f"Trying again with simple JQL: {search_url}")
                response = requests.get(search_url, headers=get_auth_headers(pat), timeout=10)
                
                if response.status_code == 200:
                    results = response.json()
                    jira_data = results.get("issues", [])
                    print(f"Found {len(jira_data)} tickets with fallback query")
        except Exception as e:
            print(f"Error fetching tickets: {str(e)}")
        
        # Create a formatted representation of tickets
        tickets_text = ""
        if jira_data:
            tickets_text = "Here are some recent Jira tickets:\n\n"
            for issue in jira_data:
                key = issue.get("key", "Unknown")
                summary = issue.get("fields", {}).get("summary", "No summary")
                status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")
                tickets_text += f"- {key}: {summary} (Status: {status})\n"
        
        # Create the full prompt with question and Jira data
        full_prompt = f"User question: {question}\n\n"
        if tickets_text:
            full_prompt += tickets_text
        else:
            full_prompt += "No Jira tickets were found to provide context for your question."
        
        # Store debug info
        debug_info = {
            "question": question,
            "jira_url": jira_url,
            "project_key": project_key,
            "tickets_found": len(jira_data),
            "prompt_length": len(full_prompt)
        }
        
        print(f"Sending prompt to LLM (length: {len(full_prompt)} chars)")
        
        try:
            # Generate response with appropriate system prompt
            system_prompt = """You are a helpful Jira assistant that answers questions about Jira projects and tickets.
If you have Jira ticket data available, use it to answer the question. If not, explain that you don't have the data needed."""
            
            response = llm_service.generate_response(
                prompt=full_prompt,
                system_prompt=system_prompt
            )
            
            print(f"Received response from LLM (length: {len(response)} chars)")
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            flash(f"Error generating response: {str(e)}", "danger")
            response = f"I'm sorry, but I encountered an error while processing your request: {str(e)}"
    
    return render_template("llm_chat.html", 
                          question=question, 
                          response=response,
                          llm_available=llm_service is not None,
                          debug_info=debug_info)
# Add this route to your existing app.py file

@app.route("/simple_chat", methods=["GET", "POST"])
def simple_chat():
    """Ultra-simple chat that will definitely work."""
    response = None
    question = None
    
    if request.method == "POST":
        question = request.form.get("question", "")
        
        try:
            # Use the LLM service directly - skip Jira for now
            response = llm_service.generate_response(
                prompt=f"User asked: {question}",
                system_prompt="You are a helpful assistant."
            )
        except Exception as e:
            response = f"Error: {str(e)}"
    
    # Render a simple template
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Chat</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container mt-5">
            <h1>Simple Chat (No Jira Integration)</h1>
            
            <div class="card mt-4">
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3">
                            <label for="question" class="form-label">Your Question:</label>
                            <input type="text" class="form-control" id="question" name="question" 
                                   value="{question or ''}" required>
                        </div>
                        <button type="submit" class="btn btn-primary">Ask</button>
                    </form>
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
        </div>
    </body>
    </html>
    """

@app.route("/llm_status", methods=["GET"])
def llm_status():
    """Check the status of the LLM service."""
    if llm_service is None:
        return jsonify({
            "status": "unavailable",
            "message": "LLM service is not configured or failed to initialize."
        })
    
    try:
        # Test the LLM service with a simple request
        test_response = llm_service.generate_response("Hello, this is a test message.")
        
        return jsonify({
            "status": "available",
            "message": "LLM service is working correctly.",
            "test_response": test_response[:50] + "..." if len(test_response) > 50 else test_response
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"LLM service encountered an error: {str(e)}"
        })

# Add an error handler for 404 (Page Not Found) errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Debugging and Diagnostics Routes
@app.route("/debug/ticket/<ticket_key>")
def debug_ticket(ticket_key):
    """Debug endpoint to check ticket data."""
    if "jira_url" not in session or "pat" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    jira_url = session["jira_url"]
    pat = session["pat"]
    
    ticket_data = get_ticket_details(jira_url, pat, ticket_key)
    
    return jsonify({
        "ticket_exists": ticket_data is not None,
        "fields_available": list(ticket_data["fields"].keys()) if ticket_data else [],
        "llm_available": llm_service is not None
    })

import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('werkzeug').setLevel(logging.INFO)

@app.route("/diagnostics")
def diagnostics():
    """Show system diagnostic information."""
    import sys
    import flask
    import pkg_resources
    
    # Check if we're connected to Jira
    jira_connected = "jira_url" in session and "pat" in session
    jira_url = session.get("jira_url", "Not connected")
    
    # Get installed packages
    required_packages = ["requests", "python-dotenv", "flask"]
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    
    packages = []
    for pkg_name in required_packages:
        packages.append({
            "name": pkg_name,
            "version": installed_packages.get(pkg_name, "Not installed"),
            "installed": pkg_name in installed_packages,
            "required": True
        })
    
    # Add optional packages
    optional_packages = ["pandas", "matplotlib", "numpy"]
    for pkg_name in optional_packages:
        if pkg_name in installed_packages:
            packages.append({
                "name": pkg_name,
                "version": installed_packages.get(pkg_name),
                "installed": True,
                "required": False
            })
    
    return render_template("diagnostics.html",
                          flask_version=flask.__version__,
                          python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                          debug_mode=app.debug,
                          llm_available=llm_service is not None,
                          jira_connected=jira_connected,
                          jira_url=jira_url,
                          packages=packages)

# Modify the app.run section at the bottom
if __name__ == "__main__":
    # Print application status
    print(f"INFO: Starting Flask app with LLM service: {llm_service is not None}")
    if llm_service is None:
        print("WARNING: LLM features will be disabled.")
    
    try:
        app.run(debug=True)
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        print(traceback.format_exc())
