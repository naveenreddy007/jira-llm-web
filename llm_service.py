import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMService:
    """A generic LLM service that can work with various API providers."""
    
    def __init__(self):
        # Try to load API key from environment
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        
        if not self.api_key:
            print("WARNING: No LLM API key found. Please add it to your .env file.")
            raise ValueError("No LLM API key found in environment variables")
        
        # Default to DeepSeek API, but can be overridden via environment variable
        self.api_url = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        
        # Determine API provider from the URL
        if "deepseek" in self.api_url:
            self.provider = "deepseek"
        elif "openai" in self.api_url:
            self.provider = "openai"
        else:
            self.provider = "unknown"
        
        print(f"INFO: Using LLM provider: {self.provider} with model: {self.model}")
    
    def generate_response(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1000):
        """Generate a response from the LLM API."""
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Create payload based on provider
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Headers with authorization
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"DEBUG: Sending request to LLM API ({self.provider})")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            
            # Log the response status
            print(f"DEBUG: Received response with status code {response.status_code}")
            
            if response.status_code != 200:
                print(f"ERROR: API returned error: {response.status_code}")
                print(f"Response text: {response.text[:500]}")
                return f"Error: The LLM API returned status code {response.status_code}"
            
            # Parse the response
            result = response.json()
            
            # Extract the response text based on provider format
            if self.provider in ["deepseek", "openai"]:
                # Both DeepSeek and OpenAI use similar response formats
                return result["choices"][0]["message"]["content"]
            else:
                # Generic fallback - attempt to extract text from any format
                print(f"DEBUG: Using generic response parsing for unknown provider")
                print(f"DEBUG: Response structure: {json.dumps(result)[:200]}...")
                
                # Try several common response formats
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        return choice["message"]["content"]
                    elif "text" in choice:
                        return choice["text"]
                
                if "result" in result:
                    return result["result"]
                
                if "response" in result:
                    return result["response"]
                
                # If we can't figure it out, return the raw response
                return f"Could not parse response. Raw response: {json.dumps(result)[:500]}"
            
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the LLM API. Please check your internet connection and API URL."
        except requests.exceptions.Timeout:
            return "Error: Request to LLM API timed out. The service might be overloaded or down."
        except json.JSONDecodeError:
            return f"Error: Could not parse API response as JSON. Raw response: {response.text[:500]}"
        except Exception as e:
            return f"Error: {str(e)}"

class MockLLM:
    """A fallback LLM service that returns predefined responses."""
    
    def generate_response(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1000):
        """Return a mock response."""
        # Log the received prompt
        print(f"MockLLM received prompt: {prompt[:100]}...")
        
        # Detect what kind of response is expected based on the prompt
        if "summarize" in prompt.lower() or "summary" in prompt.lower():
            return "This is a mock summary generated because the LLM service is not properly configured. The actual ticket would be summarized here in 2-3 concise sentences."
        
        elif "categorize" in prompt.lower() or "category" in prompt.lower():
            return "Feature Request"
        
        elif "response" in prompt.lower() or "reply" in prompt.lower():
            return "Thank you for reporting this issue. Our team is reviewing it and will update you shortly with more information. In the meantime, please let us know if you have any additional details that might help us address this more effectively."
        
        else:
            return f"This is a mock response to your query: '{prompt[:50]}...'. The LLM service is not properly configured. Please check your API key and connection."

def get_llm_service():
    """Get an LLM service instance, falling back to a mock if needed."""
    try:
        return LLMService()
    except Exception as e:
        print(f"WARNING: Using MockLLM due to error: {str(e)}")
        return MockLLM()

# Helper functions for Jira + LLM integration

def summarize_ticket(llm, ticket_data):
    """Generate a summary of a Jira ticket using LLM."""
    prompt = f"""
    Please provide a concise summary of this Jira ticket:
    
    Title: {ticket_data.get('summary', 'No title')}
    Description: {ticket_data.get('description', 'No description')}
    Status: {ticket_data.get('status', 'Unknown')}
    Priority: {ticket_data.get('priority', 'Unknown')}
    Reporter: {ticket_data.get('reporter', 'Unknown')}
    
    Provide a 2-3 sentence summary that captures the key points.
    """
    
    print(f"DEBUG - Summarize ticket prompt: {prompt[:200]}...")
    response = llm.generate_response(prompt)
    print(f"DEBUG - Summarize ticket response: {response[:200]}...")
    return response

def categorize_ticket(llm, ticket_data):
    """Categorize a Jira ticket using LLM."""
    prompt = f"""
    Based on the information below, categorize this Jira ticket into one of the following:
    - Bug
    - Feature Request
    - Documentation
    - Support Request
    - Infrastructure
    - Security Issue
    
    Title: {ticket_data.get('summary', 'No title')}
    Description: {ticket_data.get('description', 'No description')}
    
    Reply ONLY with the category name, nothing else.
    """
    
    return llm.generate_response(prompt)

def generate_response_suggestion(llm, ticket_data):
    """Generate a suggested response for a ticket."""
    prompt = f"""
    Please draft a helpful, professional response to this Jira ticket:
    
    Title: {ticket_data.get('summary', 'No title')}
    Description: {ticket_data.get('description', 'No description')}
    Status: {ticket_data.get('status', 'Unknown')}
    Priority: {ticket_data.get('priority', 'Unknown')}
    
    The response should acknowledge the issue, provide next steps if possible, and maintain a helpful tone.
    """
    
    return llm.generate_response(prompt)

def analyze_project_tickets(llm, project_stats):
    """Generate insights about a project based on ticket data."""
    prompt = f"""
    Based on the following Jira project statistics, provide 3-5 key insights and recommendations:
    
    Project: {project_stats.get('name', 'Unknown')}
    Total Tickets: {project_stats.get('total_tickets', 0)}
    Open Tickets: {project_stats.get('open_tickets', 0)}
    Tickets by Priority:
    {project_stats.get('priority_breakdown', 'No data')}
    Average Resolution Time: {project_stats.get('avg_resolution_time', 'Unknown')}
    
    Focus on identifying patterns, bottlenecks, and suggestions for improving project health.
    """
    
    return llm.generate_response(prompt)

# If run directly, test the LLM service
if __name__ == "__main__":
    print("Testing LLM service...")
    try:
        llm = get_llm_service()
        response = llm.generate_response("Hello, this is a test message. Please respond with a short greeting.")
        print("\nResponse from LLM:")
        print(response)
    except Exception as e:
        print(f"Error testing LLM service: {e}")