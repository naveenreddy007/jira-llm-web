from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import requests
import os
from dotenv import load_dotenv

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

# Initialize LLM service
llm_service = None
if llm_module_imported:
    try:
        llm_service = get_llm_service()
        print("INFO: LLM service initialized successfully")
    except Exception as e:
        print(f"WARNING: Failed to initialize LLM service: {e}")

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
    
    if request.method == "POST":
        question = request.form.get("question", "")
        
        try:
            # Generate response
            response = llm_service.generate_response(
                prompt=question,
                system_prompt="You are a helpful assistant that answers questions about Jira projects and tickets."
            )
        except Exception as e:
            flash(f"Error generating response: {str(e)}", "danger")
            response = f"I'm sorry, but I encountered an error while processing your request: {str(e)}"
    
    return render_template("llm_chat.html", 
                          question=question, 
                          response=response,
                          llm_available=llm_service is not None)

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

if __name__ == "__main__":
    # Print application status
    print(f"INFO: Starting Flask app with LLM service: {llm_service is not None}")
    if llm_service is None:
        print("WARNING: LLM features will be disabled.")
    
    app.run(debug=True)