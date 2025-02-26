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