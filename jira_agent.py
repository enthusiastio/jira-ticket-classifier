import logging
import os
import json
import re
import dotenv
import requests
from requests.auth import HTTPBasicAuth
from langchain_openai import ChatOpenAI

# Load environment variables
dotenv.load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# Define LLM
llm = ChatOpenAI(temperature=0.0, model="gpt-3.5-turbo", openai_api_key=os.getenv("OPENAI_API_KEY"))

# Helper functions for software products management
def load_software_products():
    """Load software products from JSON file"""
    products_file = os.path.join(os.path.dirname(__file__), 'configuration', 'software_products.json')
    try:
        if os.path.exists(products_file):
            with open(products_file, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Products file not found: {products_file}")
            return {}
    except Exception as e:
        logger.error(f"Error loading software products: {e}")
        return {}

def save_software_products(products):
    """Save software products to JSON file"""
    products_file = os.path.join(os.path.dirname(__file__), 'configuration', 'software_products.json')
    try:
        with open(products_file, 'w') as f:
            json.dump(products, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving software products: {e}")
        return False

# Helper functions for extra prompt info management
def load_extra_info():
    """Load extra prompt info from JSON file"""
    info_file = os.path.join(os.path.dirname(__file__), 'configuration', 'extra_info.json')
    try:
        if os.path.exists(info_file):
            with open(info_file, 'r') as f:
                data = json.load(f)
                return data.get('prompt_info', [])
        else:
            logger.warning(f"Extra info file not found: {info_file}")
            return []
    except Exception as e:
        logger.error(f"Error loading extra info: {e}")
        return []

def save_extra_info(info_items):
    """Save extra prompt info to JSON file"""
    info_file = os.path.join(os.path.dirname(__file__), 'configuration', 'extra_info.json')
    try:
        with open(info_file, 'w') as f:
            json.dump({"prompt_info": info_items}, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving extra info: {e}")
        return False

# Load software products and extra info from files
software_products = load_software_products()
extra_info = load_extra_info()

# Labels for work types
labels = ["Design", "Development", "Maintenance", "Devops", "Testing", "Documentation", "Management"]


# Jira API class
class JiraAPI:
    @staticmethod
    def get_auth_credentials():
        """Get authentication credentials from the Flask session or environment variables as fallback"""
        # Import Flask dependencies dynamically to avoid circular imports
        from flask import session, current_app
        import base64
        
        # First check if credentials are in the session (preferred)
        if session and 'jira_username' in session and 'jira_password' in session and 'jira_host' in session:
            # Get base URL from session
            base_url = session.get('jira_host')
            # Get username from session
            username = session.get('jira_username')
            # Get password from session (decode from base64)
            try:
                password = base64.b64decode(session.get('jira_password', '')).decode()
            except Exception:
                password = ''  # Reset password if decoding fails
                
            return {
                'base_url': base_url,
                'username': username,
                'password': password
            }
        
        # Fallback to environment variables (legacy support)
        return {
            'base_url': os.getenv("JIRA_HOST"),
            'username': os.getenv("JIRA_USER"),
            'password': os.getenv("JIRA_PASSWORD")
        }

    @staticmethod
    def test_connection(base_url, username, password):
        """Test JIRA API connection with provided credentials"""
        test_url = f"{base_url}/rest/api/2/myself"
        
        try:
            response = requests.get(
                test_url,
                auth=HTTPBasicAuth(username, password),
                headers={"Accept": "application/json"}
            )
            
            if response.status_code == 200:
                return {"success": True, "user": response.json().get('displayName')}
            else:
                return {"success": False, "error": f"API returned status code {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def fetch_tickets(sprint_id=None):
        """Fetch Jira tickets using the REST API."""
        # Get auth credentials
        creds = JiraAPI.get_auth_credentials()
        base_url = creds['base_url']
        username = creds['username']
        password = creds['password']
        
        search_url = f"{base_url}/rest/api/2/search"
        
        jql_query = f'project = "Scientific Web Applications" AND component is EMPTY AND sprint in ({sprint_id})'
            
        params = {"jql": jql_query}

        # Basic authentication with username and password
        response = requests.get(
            search_url,
            params=params,
            auth=HTTPBasicAuth(username, password),
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch tickets: {response.status_code} {response.text}")

        # Parse response JSON
        issues = response.json().get("issues", [])
        tickets = [
            {"id": issue["id"], 
             "title": issue["fields"]["summary"], 
             "description": issue["fields"]["description"] or "", 
             "creator": issue["fields"]["creator"]['name'],
             "key": issue["key"],
             "components": ", ".join(comp["name"] for comp in issue['fields']["components"])
             }
            for issue in issues
        ]

        return tickets

    @staticmethod
    def update_ticket(ticket_id, fields):
        """Update Jira ticket using the REST API."""
        # Get auth credentials
        creds = JiraAPI.get_auth_credentials()
        base_url = creds['base_url']
        username = creds['username']
        password = creds['password']
        
        update_url = f"{base_url}/rest/api/2/issue/{ticket_id}"
        payload = {"fields": fields}

        response = requests.put(
            update_url,
            auth=HTTPBasicAuth(username, password),
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )

        if response.status_code != 204:
            raise Exception(f"Failed to update ticket: {response.status_code} {response.text}")
       
        return response


def classify_ticket(ticket, software_products=None):
    """LLM-based classification."""
    # Always reload the latest software products and extra info before classification
    if software_products is None:
        software_products = load_software_products()
    
    # Build project descriptions dynamically from `software_products`
    project_descriptions = "\n".join([
        f"{name} - {details['description']} (Authors always are one of: {', '.join(details['likely_authors'])})"
        for name, details in software_products.items()
    ])
    
    # Always load the latest extra info
    current_extra_info = load_extra_info()
    extra_info_text = "\n".join(current_extra_info) if current_extra_info else "No extra info provided."
    
    # Construct the prompt
    prompt = f"""
    You are an expert in software management. You need determine which software product is the ticket related to.:
    Ticket: {ticket['key']}
    Title: {ticket['title']}
    Description: {ticket['description']}
    Author: {ticket['creator']}
    
    Here is the list of possible software products:
    {project_descriptions}
    
    2. What is the type of work? Options: {", ".join(labels)}
    Respond in JSON format with "component", "work_type", "confidence" and "reason".
    Reason is the reason why component has the value you set.
    Component may NOT have value any other than the ones listed above.

    3. Extra info: 
    {extra_info_text}
    
    Your response MUST be valid JSON and ONLY JSON. No other text.
    Example response format: 
    {{"component": "scicat", "work_type": "Design", "confidence": "High", "reason": "This is about SciCat metadata features"}}
    """

    print(f"Prompt: {prompt}")
    
    # Call the LLM with the prompt
    response = llm.invoke(prompt)
    
    # Extract content from AIMessage before parsing as JSON
    response_content = response.content
    
    # Add error handling for JSON parsing
    try:
        response_json = json.loads(response_content)
    except json.JSONDecodeError:
        # If we can't parse the JSON, try to extract JSON from the response using regex
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, response_content, re.DOTALL)
        
        if match:
            try:
                response_json = json.loads(match.group(0))
            except json.JSONDecodeError:
                # If still can't parse, use a fallback
                logger.warning(f"Failed to parse JSON from response: {response_content}")
                response_json = {
                    "component": "scicat" if "scicat" in response_content.lower() else "user_office",
                    "work_type": "Design" if "investigation" in ticket['title'].lower() or "investigate" in ticket['title'].lower() else "Development",
                    "confidence": "Low",
                    "reason": "Failed to parse JSON response from LLM"
                }
        else:
            # No JSON-like content found, use fallback
            logger.warning(f"No JSON-like content found in response: {response_content}")
            response_json = {
                "component": "scicat" if "scicat" in response_content.lower() else "user_office",
                "work_type": "Design" if "investigation" in ticket['title'].lower() or "investigate" in ticket['title'].lower() else "Development",
                "confidence": "Low",
                "reason": "Failed to parse JSON response from LLM"
            }
    
    if response_json['work_type'] not in labels:
        response_json['confidence'] = 'Low'
        response_json['reason'] = 'Work type is not in the list of labels'
        
        prompt2 = f"""
        Classify this ticket with one of these labels EXACTLY: {labels}
        Ticket: {ticket['key']}
        Title: {ticket['title']}
        Description: {ticket['description']}
        Author: {ticket['creator']}
        
        Respond with ONLY ONE WORD from the labels list. No explanations or JSON.
        """
        response2 = llm.invoke(prompt2)
        response2_content = response2.content.strip()
        
        # Check if the response is one of the valid labels
        valid_label = False
        for label in labels:
            if label.lower() in response2_content.lower():
                response_json['work_type'] = label
                valid_label = True
                break
                
        if not valid_label:
            logger.warning(f"Invalid label from second attempt: {response2_content}")
            response_json['work_type'] = "Development"  # Default to Development if still invalid

    return response_json


def process_ticket(ticket, return_details=False, preview_only=False):
    """Process a single ticket.
    If preview_only is True, it will not perform any updates but just check if updates are possible.
    """
    result = {
        "classification": None,
        "updated": False,
        "can_update": False,  # New field for preview mode
        "skip_reason": ""
    }
    
    # If component is already set, skip
    if(ticket['components']):
        result["skip_reason"] = "Component already set"
        if return_details:
            return result
        return
    
    # Classify the ticket
    classification = classify_ticket(ticket)
    result["classification"] = classification
    print(f"Classification: {classification}")
    
    if classification["confidence"] == 'High':
        # Check if component is in software_products
        if classification['component'] not in software_products:
            logger.warning(f"Component {classification['component']} is not in software products. Skipping...")
            result["skip_reason"] = f"Component {classification['component']} is not in software products"
        else:
            # In preview mode, just mark as can be updated
            result["can_update"] = True
            
            # Only perform update if not in preview mode
            if not preview_only:
                # High confidence: Auto-update
                logger.info(f"Updating ticket {ticket['key']}. {ticket['title']}, Details: {classification}")
                
                # Get component ID
                componentId = software_products[classification['component']]['componentId']
                
                # Update the ticket
                try:
                    JiraAPI.update_ticket(ticket["id"], {
                        "components": [{"id": componentId}],
                        "labels": [classification["work_type"]]
                    })
                    result["updated"] = True
                except Exception as e:
                    logger.error(f"Error updating ticket {ticket['key']}: {e}")
                    result["skip_reason"] = f"Error updating ticket: {str(e)}"
    else:
        # Low confidence: Log and ask for confirmation
        logger.warning(f"Low confidence for Ticket {ticket['id']}. Details: {classification}")
        result["skip_reason"] = "Low confidence classification"
    
    if return_details:
        return result

def update_ticket(ticket, classification):
    """Perform the actual update of a ticket based on classification"""
    result = {
        "updated": False,
        "error": ""
    }
    
    # Skip if no ticket or classification provided
    if not ticket or not classification:
        result["error"] = "Missing ticket or classification data"
        return result
    
    # Skip if component is not in software_products
    if classification['component'] not in software_products:
        result["error"] = f"Component {classification['component']} is not in software products"
        return result
    
    try:
        # Get component ID
        componentId = software_products[classification['component']]['componentId']
        
        # Update the ticket
        logger.info(f"Updating ticket {ticket['key']}. {ticket['title']}, Details: {classification}")
        JiraAPI.update_ticket(ticket["id"], {
            "components": [{"id": componentId}],
            "labels": [classification["work_type"]]
        })
        result["updated"] = True
    except Exception as e:
        logger.error(f"Error updating ticket {ticket['key']}: {e}")
        result["error"] = str(e)
    
    return result

# Main function to run the agent
def jira_agent(sprint_ids=None, preview_only=False):
    """Run the Jira agent for the specified sprint IDs."""
    results = []
    
    # If no sprint IDs are provided, use the default one
    sprint_ids = sprint_ids or ["1412"]
    
    for sprint_id in sprint_ids:
        tickets = JiraAPI.fetch_tickets(sprint_id=sprint_id)
        sprint_results = {
            "sprint_id": sprint_id,
            "tickets_processed": len(tickets),
            "details": []
        }
        
        for ticket in tickets:
            result = process_ticket(ticket, return_details=True, preview_only=preview_only)
            sprint_results["details"].append({
                "key": ticket["key"],
                "title": ticket["title"],
                "result": result
            })
        
        results.append(sprint_results)
    
    return results


# Run Agent if executed directly
if __name__ == "__main__":
    try:
        jira_agent()
    except Exception as e:
        logger.error(f"Error: {e}")