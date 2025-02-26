import requests
import json
import logging
from urllib.parse import quote

# Configure logging
logger = logging.getLogger(__name__)

class JiraLLMIntegration:
    """Class for handling LLM-powered Jira queries and analysis."""
    
    def __init__(self, llm_service):
        """Initialize with LLM service."""
        self.llm_service = llm_service
    
    def get_auth_headers(self, pat):
        """Return headers for Jira authentication."""
        return {
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json"
        }
    
    def natural_to_jql(self, natural_language_request):
        """Convert natural language to JQL using LLM."""
        prompt = f"""
        Convert this natural language request to a valid Jira JQL query:
        REQUEST: {natural_language_request}
        
        A reminder about JQL:
        - Use AND, OR, NOT for logical operators
        - For string fields, use = "Value" (with quotes)
        - For dates, use operators like >=, <=, =
        - Common fields: project, status, priority, assignee, reporter, created, updated
        - For in-progress tickets: status = "In Progress"
        - For high priority: priority = "High" OR priority = "Highest"
        
        Respond ONLY with the valid JQL query, nothing else.
        """
        
        try:
            jql_query = self.llm_service.generate_response(prompt).strip()
            logger.debug(f"Generated JQL query: {jql_query}")
            return jql_query
        except Exception as e:
            logger.error(f"Error generating JQL query: {str(e)}")
            return f"project IS NOT EMPTY"  # Safe fallback query
    
    def execute_jql_query(self, jira_url, pat, jql_query, max_results=50):
        """Execute a JQL query against the Jira API."""
        # URL encode the JQL query
        encoded_jql = quote(jql_query)
        search_url = f"{jira_url}/rest/api/2/search?jql={encoded_jql}&maxResults={max_results}"
        
        try:
            logger.debug(f"Executing JQL query: {jql_query}")
            response = requests.get(
                search_url, 
                headers=self.get_auth_headers(pat), 
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"JQL query failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Query failed with status {response.status_code}",
                    "message": response.text
                }
            
            return {
                "success": True,
                "data": response.json()
            }
                
        except Exception as e:
            logger.error(f"Error executing JQL query: {str(e)}")
            return {
                "success": False,
                "error": f"Error executing query: {str(e)}"
            }
    
    def analyze_tickets(self, natural_language_request, tickets_data, total_count):
        """Use LLM to analyze ticket data."""
        # Prepare a simplified version of the tickets to avoid token limits
        simplified_tickets = []
        
        for ticket in tickets_data.get("issues", [])[:15]:  # Limit to 15 tickets for analysis
            fields = ticket.get("fields", {})
            simplified_ticket = {
                "key": ticket.get("key"),
                "summary": fields.get("summary"),
                "status": fields.get("status", {}).get("name") if fields.get("status") else None,
                "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
                "created": fields.get("created"),
                "updated": fields.get("updated")
            }
            simplified_tickets.append(simplified_ticket)
        
        # Create prompt for the LLM
        prompt = f"""
        Analyze these Jira tickets based on the natural language request: "{natural_language_request}"
        
        Total matching tickets: {total_count}
        Tickets sample (showing {len(simplified_tickets)} of {total_count}):
        {json.dumps(simplified_tickets, indent=2)}
        
        Provide:
        1. Summary of findings - What patterns do you see across these tickets?
        2. Key insights - What's important to notice about these tickets?
        3. Recommendations - What actions should be taken based on this data?
        
        Format your response in HTML with appropriate headings (h3, h4) and paragraphs.
        """
        
        try:
            analysis = self.llm_service.generate_response(prompt)
            logger.debug(f"Generated analysis (length: {len(analysis)})")
            return analysis
        except Exception as e:
            logger.error(f"Error generating analysis: {str(e)}")
            return f"<h3>Analysis Error</h3><p>Unable to generate analysis: {str(e)}</p>"
    
    def process_natural_language_query(self, jira_url, pat, natural_language_request):
        """Process a natural language query end-to-end."""
        # Step 1: Convert to JQL
        jql_query = self.natural_to_jql(natural_language_request)
        
        # Step 2: Execute the query
        query_result = self.execute_jql_query(jira_url, pat, jql_query)
        
        if not query_result.get("success"):
            return {
                "success": False,
                "jql": jql_query,
                "error": query_result.get("error"),
                "message": query_result.get("message", "Unknown error")
            }
        
        tickets_data = query_result.get("data", {})
        total_count = tickets_data.get("total", 0)
        
        # Step 3: Analyze the results
        analysis = self.analyze_tickets(
            natural_language_request, 
            tickets_data, 
            total_count
        )
        
        return {
            "success": True,
            "jql": jql_query,
            "tickets": tickets_data.get("issues", []),
            "total": total_count,
            "analysis": analysis
        }