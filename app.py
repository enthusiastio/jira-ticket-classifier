from flask import Flask, render_template, request, jsonify, session
import logging
import os
import dotenv
import json
from flask_session import Session
from jira_agent import (JiraAPI, classify_ticket, process_ticket, update_ticket, 
                       load_software_products, save_software_products,
                       load_extra_info, save_extra_info)

# Load environment variables
dotenv.load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# Initialize Flask app
app = Flask(__name__)
# Fixed secret key for session management (more reliable than random key)
app.secret_key = 'jira_ticket_classifier_secret_key_2025'
# Configure session to be more reliable
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session lifetime
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_PERMANENT'] = True

# Initialize the session extension
Session(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
def products_page():
    return render_template('products.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all software products"""
    products = load_software_products()
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def add_product():
    """Add a new software product"""
    try:
        data = request.json
        product_name = data.get('name', '').strip().lower()
        component_id = data.get('componentId', '').strip()
        description = data.get('description', '').strip()
        authors_str = data.get('authors', '').strip()
        
        # Validate input
        if not product_name or not component_id or not description or not authors_str:
            return jsonify({
                "status": "error", 
                "message": "All fields are required"
            }), 400
        
        # Parse authors
        likely_authors = [author.strip() for author in authors_str.split(',') if author.strip()]
        
        # Load existing products
        products = load_software_products()
        
        # Check if product already exists
        if product_name in products:
            return jsonify({
                "status": "error", 
                "message": f"Product '{product_name}' already exists"
            }), 400
        
        # Add new product
        products[product_name] = {
            "componentId": component_id,
            "description": description,
            "likely_authors": likely_authors
        }
        
        # Save updated products
        if save_software_products(products):
            return jsonify({
                "status": "success", 
                "message": f"Product '{product_name}' added successfully"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to save product data"
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding product: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/products/<string:name>', methods=['PUT'])
def update_product(name):
    """Update an existing software product"""
    try:
        data = request.json
        component_id = data.get('componentId', '').strip()
        description = data.get('description', '').strip()
        authors_str = data.get('authors', '').strip()
        
        # Validate input
        if not component_id or not description or not authors_str:
            return jsonify({
                "status": "error", 
                "message": "All fields are required"
            }), 400
        
        # Parse authors
        likely_authors = [author.strip() for author in authors_str.split(',') if author.strip()]
        
        # Load existing products
        products = load_software_products()
        
        # Check if product exists
        if name not in products:
            return jsonify({
                "status": "error", 
                "message": f"Product '{name}' not found"
            }), 404
        
        # Update product
        products[name] = {
            "componentId": component_id,
            "description": description,
            "likely_authors": likely_authors
        }
        
        # Save updated products
        if save_software_products(products):
            return jsonify({
                "status": "success", 
                "message": f"Product '{name}' updated successfully"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to save product data"
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/products/<string:name>', methods=['DELETE'])
def delete_product(name):
    """Delete a software product"""
    try:
        # Load existing products
        products = load_software_products()
        
        # Check if product exists
        if name not in products:
            return jsonify({
                "status": "error", 
                "message": f"Product '{name}' not found"
            }), 404
        
        # Remove product
        del products[name]
        
        # Save updated products
        if save_software_products(products):
            return jsonify({
                "status": "success", 
                "message": f"Product '{name}' deleted successfully"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to save product data"
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/extra-info', methods=['GET'])
def get_extra_info():
    """Get all extra info items"""
    info_items = load_extra_info()
    return jsonify(info_items)

@app.route('/api/extra-info', methods=['POST'])
def add_extra_info():
    """Add a new extra info item"""
    try:
        data = request.json
        info_text = data.get('text', '').strip()
        
        if not info_text:
            return jsonify({
                "status": "error", 
                "message": "Info text is required"
            }), 400
        
        # Load existing items
        info_items = load_extra_info()
        
        # Check if item already exists
        if info_text in info_items:
            return jsonify({
                "status": "error", 
                "message": "This item already exists"
            }), 400
        
        # Add new item
        info_items.append(info_text)
        
        # Save updated items
        if save_extra_info(info_items):
            return jsonify({
                "status": "success", 
                "message": "Extra info item added successfully"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to save extra info"
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding extra info: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/extra-info/<int:index>', methods=['PUT'])
def update_extra_info(index):
    """Update an existing extra info item"""
    try:
        data = request.json
        info_text = data.get('text', '').strip()
        
        if not info_text:
            return jsonify({
                "status": "error", 
                "message": "Info text is required"
            }), 400
        
        # Load existing items
        info_items = load_extra_info()
        
        # Check if index is valid
        if index < 0 or index >= len(info_items):
            return jsonify({
                "status": "error", 
                "message": "Invalid item index"
            }), 404
        
        # Update item
        info_items[index] = info_text
        
        # Save updated items
        if save_extra_info(info_items):
            return jsonify({
                "status": "success", 
                "message": "Extra info item updated successfully"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to save extra info"
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating extra info: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/extra-info/<int:index>', methods=['DELETE'])
def delete_extra_info(index):
    """Delete an extra info item"""
    try:
        # Load existing items
        info_items = load_extra_info()
        
        # Check if index is valid
        if index < 0 or index >= len(info_items):
            return jsonify({
                "status": "error", 
                "message": "Invalid item index"
            }), 404
        
        # Remove item
        del info_items[index]
        
        # Save updated items
        if save_extra_info(info_items):
            return jsonify({
                "status": "success", 
                "message": "Extra info item deleted successfully"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to save extra info"
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting extra info: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/preview-tickets', methods=['POST'])
def preview_jira_tickets():
    try:
        # Get sprint IDs from the request
        data = request.json
        sprint_ids = data.get('sprint_ids', [])
        
        if not sprint_ids:
            return jsonify({"status": "error", "message": "No sprint IDs provided"}), 400
        
        results = []
        all_tickets = []
        
        # Process each sprint (preview only)
        for sprint_id in sprint_ids:
            # Get tickets for the sprint
            tickets = JiraAPI.fetch_tickets(sprint_id=sprint_id)
            
            sprint_result = {
                "sprint_id": sprint_id,
                "tickets_processed": 0,
                "tickets_updatable": 0,
                "tickets_skipped": 0,
                "ticket_details": []
            }
            
            # Process each ticket for preview
            for ticket in tickets:
                result = process_ticket(ticket, return_details=True, preview_only=True)
                sprint_result["tickets_processed"] += 1
                
                # Store ALL tickets with classification data, regardless of confidence
                # This allows the frontend to override low-confidence tickets
                if result.get("classification"):
                    ticket_item = {
                        "ticket": ticket,
                        "classification": result.get("classification", {}),
                        "previewed": result.get("can_update", False)  # Only high confidence tickets are initially set for update
                    }
                    all_tickets.append(ticket_item)
                    
                    if result.get("can_update", False):
                        sprint_result["tickets_updatable"] += 1
                    else:
                        sprint_result["tickets_skipped"] += 1
                else:
                    # Tickets without classification data are just skipped
                    sprint_result["tickets_skipped"] += 1
                    
                sprint_result["ticket_details"].append({
                    "key": ticket.get("key", ""),
                    "title": ticket.get("title", ""),
                    "classification": result.get("classification", {}),
                    "can_update": result.get("can_update", False),
                    "skip_reason": result.get("skip_reason", "")
                })
            
            results.append(sprint_result)
        
        # Log the number of tickets being stored
        logger.info(f"Storing {len(all_tickets)} tickets in session (including both high and low confidence)")
        
        # Store the previewed tickets in session for later update
        session['previewed_tickets'] = json.dumps(all_tickets, default=str)
        session['sprint_ids'] = sprint_ids
        
        return jsonify({
            "status": "success", 
            "message": f"Preview completed for {len(sprint_ids)} sprints", 
            "results": results
        })
    
    except Exception as e:
        logger.error(f"Error previewing tickets: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update-tickets', methods=['POST'])
def update_jira_tickets():
    try:
        # Get previewed tickets from session
        previewed_tickets_json = session.get('previewed_tickets')
        if not previewed_tickets_json:
            return jsonify({"status": "error", "message": "No previewed tickets found. Please run preview first"}), 400
            
        previewed_tickets = json.loads(previewed_tickets_json)
        sprint_ids = session.get('sprint_ids', [])
        
        # Get any user-provided overrides
        data = request.json or {}
        overrides = data.get('overrides', {})
        
        # Log for debugging
        logger.info(f"Received update request with overrides: {overrides}")
        logger.info(f"Total tickets in session: {len(previewed_tickets)}")
        
        # First pass: Apply overrides and mark tickets as previewed
        all_tickets = []
        for item in previewed_tickets:
            ticket = item.get("ticket", {})
            ticket_key = ticket.get("key", "")
            
            # Apply any user overrides and mark the ticket for update
            if ticket_key in overrides:
                ticket_overrides = overrides[ticket_key]
                classification = item.get("classification", {})
                
                # Override component if provided
                if "component" in ticket_overrides:
                    classification["component"] = ticket_overrides["component"]
                
                # Override work_type if provided
                if "work_type" in ticket_overrides:
                    classification["work_type"] = ticket_overrides["work_type"]
                
                # Mark ticket as previewed (ready to update) since we have overrides
                item["previewed"] = True
                
                logger.info(f"Applied overrides for ticket {ticket_key}: {ticket_overrides}")
            
            all_tickets.append(item)
        
        # Second pass: Process updates
        update_results = []
        total_updated = 0
        total_failed = 0
        
        for item in all_tickets:
            ticket = item.get("ticket", {})
            classification = item.get("classification", {})
            ticket_key = ticket.get("key", "")
            
            # Only attempt to update tickets that have previewed=True
            if item.get("previewed", False):
                logger.info(f"Attempting to update ticket {ticket_key}")
                
                # Attempt the update
                result = update_ticket(ticket, classification)
                
                update_info = {
                    "key": ticket_key,
                    "title": ticket.get("title", ""),
                    "updated": result.get("updated", False),
                    "error": result.get("error", "")
                }
                
                if result.get("updated", False):
                    total_updated += 1
                    logger.info(f"Successfully updated ticket {ticket_key}")
                else:
                    total_failed += 1
                    logger.info(f"Failed to update ticket {ticket_key}: {result.get('error', '')}")
                    
                update_results.append(update_info)
        
        # Clear session after update is complete
        session.pop('previewed_tickets', None)
        session.pop('sprint_ids', None)
        
        return jsonify({
            "status": "success",
            "message": f"Updated {total_updated} tickets, {total_failed} failed",
            "sprint_ids": sprint_ids,
            "update_results": update_results
        })
        
    except Exception as e:
        logger.error(f"Error updating tickets: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)