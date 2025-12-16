"""
Dynamic API Honeypot with Realistic API Maze
Creates interconnected endpoints with logical structure and breadcrumbs
"""

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import logging
from pathlib import Path
from datetime import datetime
import json
from faker import Faker
from typing import Optional
import base64
import random
import time

# Import custom modules from src
from src.state import APIStateManager
from src.file_generator import FileGenerator
from src.llm import LLMGenerator
from src.api_generator import APIMazeGenerator

# Setup Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize
state = APIStateManager()
fake = Faker()
file_gen = FileGenerator(server_url="http://localhost:8001")
maze = APIMazeGenerator()  # API Maze Generator

try:
    llm = LLMGenerator()
    llm_enabled = True
    print("[MAZE] Gemini AI enabled for realistic responses")
except Exception as e:
    print(f"[MAZE] LLM Init Failed: {e}")
    llm = None
    llm_enabled = False

# Logging with Base64 encoding
log_dir = Path("log_files")
log_dir.mkdir(exist_ok=True)


class EncodedFileHandler(logging.FileHandler):
    """Custom handler that Base64 encodes log messages before writing"""
    def emit(self, record):
        try:
            msg = self.format(record)
            # Encode the log message
            encoded_msg = base64.b64encode(msg.encode('utf-8')).decode('utf-8')
            # Write encoded message
            with open(self.baseFilename, 'a', encoding='utf-8') as f:
                f.write(encoded_msg + '\n')
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        EncodedFileHandler(log_dir / "api_audit.log"),  # Encoded file logs
        logging.StreamHandler()  # Console logs (not encoded)
    ]
)

logger = logging.getLogger(__name__)

# ===== SPECIFIC ROUTES (these have priority) =====

@app.route("/")
def root():
    return jsonify({
        "name": "Corporate API Gateway",
        "version": "2.3.1",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "authentication": "/api/v1/auth/login",
            "api_v1": "/api/v1/",
            "api_v2": "/api/v2/admin/"
        },
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route("/health")
def health_check():
    stats = state.get_statistics()
    return jsonify({
        "status": "healthy",
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    })

# ===== AUTH ENDPOINTS (Fake Authentication) =====

@app.route("/api/v1/auth/login", methods=["POST"])
def fake_login():
    """Fake login - always succeeds and returns user token"""
    try:
        body = request.get_json(silent=True) or {}
    except:
        body = {}
    
    client_ip = request.remote_addr
    logger.warning(f"[AUTH] Login attempt from {client_ip}")
    
    return jsonify(maze.generate_auth_response("/api/v1/auth/login"))

@app.route("/api/v1/auth/elevate", methods=["POST"])
def fake_elevate():
    """Fake elevation - returns admin token if user token present"""
    authorization = request.headers.get('Authorization')
    
    if not authorization:
        return jsonify({
            "error": "Unauthorized", 
            "message": "User token required"
        }), 401
    
    logger.warning(f"[AUTH] Elevation request with token: {authorization[:20]}...")
    return jsonify(maze.generate_auth_response("/api/v1/auth/elevate"))

@app.route("/api/v1/auth/internal", methods=["POST"])
def fake_internal_auth():
    """Fake internal access - returns internal token if admin token present"""
    authorization = request.headers.get('Authorization')
    
    if not authorization or maze.fake_tokens['admin'] not in authorization:
        return jsonify({
            "error": "Forbidden", 
            "message": "Admin token required"
        }), 403
    
    logger.critical(f"[AUTH] Internal access granted!")
    return jsonify(maze.generate_auth_response("/api/v1/auth/internal"))

# ===== FILE DOWNLOAD & TRACKING =====

@app.route("/api/download/<path:filename>")
def download_file(filename):
    client_ip = request.remote_addr
    
    logger.warning(json.dumps({
        "event": "file_download",
        "ip": client_ip,
        "filename": filename
    }))
    
    try:
        if filename.endswith('.pdf'):
            filepath, beacon_id = file_gen.generate_pdf(filename, client_ip)
            state.save_beacon(beacon_id, "pdf", filename, client_ip)
        elif filename.endswith(('.xlsx', '.xls')):
            filepath, beacon_id = file_gen.generate_excel(filename, client_ip)
            state.save_beacon(beacon_id, "excel", filename, client_ip)
        elif filename.endswith('.env'):
            filepath, beacon_id = file_gen.generate_env_file(filename, client_ip)
            state.save_beacon(beacon_id, "env", filename, client_ip)
        else:
            return jsonify({"error": "File not found"}), 404
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"File generation error: {e}")
        return jsonify({"error": "Internal error"}), 500

@app.route("/track/<beacon_id>")
def track_beacon(beacon_id):
    client_ip = request.remote_addr
    beacon_data = state.activate_beacon(beacon_id, client_ip)
    
    logger.critical(json.dumps({
        "event": "BEACON_ACTIVATED",
        "beacon_id": beacon_id,
        "ip": client_ip,
        "alert": "BAIT FILE OPENED!"
    }))
    
    pixel_path = Path("static/tracking_pixel.png")
    if pixel_path.exists():
        return send_file(pixel_path, mimetype="image/png")
    return Response(b"", mimetype="image/png")

# ===== CONTEXTUAL FILE GENERATION =====

def generate_contextual_file(path, client_ip):
    """Generate contextual files based on endpoint path"""
    path_lower = path.lower()
    
    # Determine file type based on endpoint context
    if 'report' in path_lower or 'analytics' in path_lower:
        return {
            "filename": f"report_{fake.random_int(1000, 9999)}.pdf",
            "type": "pdf",
            "size": "2.3 MB",
            "description": "Analytics report"
        }
    elif 'export' in path_lower or 'data' in path_lower:
        return {
            "filename": f"export_{fake.random_int(1000, 9999)}.xlsx",
            "type": "excel",
            "size": "1.8 MB",
            "description": "Data export"
        }
    elif 'config' in path_lower or 'settings' in path_lower:
        return {
            "filename": ".env",
            "type": "env",
            "size": "421 bytes",
            "description": "Configuration file"
        }
    
    return None

# ===== DYNAMIC CATCH-ALL WITH MAZE LOGIC =====

@app.route("/<path:full_path>", methods=["GET", "POST", "PUT", "DELETE"])
def dynamic_endpoint(full_path):
    """
    Catch-all for dynamic endpoint generation with maze logic
    """
    try:
        method = request.method
        client_ip = request.remote_addr
        authorization = request.headers.get('Authorization')
        user_agent = request.headers.get('User-Agent', '')
        
        # Determine access level based on path and token
        access_level = maze.determine_access_level(full_path, authorization)
        
        # VALIDATE ENDPOINT - Reject silly paths, but tarpit directory busters
        if not maze.is_valid_endpoint(full_path, user_agent):
            logger.warning(f"[MAZE] INVALID path rejected: /{full_path}")
            return jsonify({
                "error": "Not Found",
                "message": f"The requested URL was not found on this server.",
                "path": f"/{full_path}"
            }), 404
        
        # TARPIT: Slow down directory busters
        if maze._is_directory_buster(user_agent, full_path):
            logger.warning(f"[TARPIT] Directory buster detected! Slowing down: {user_agent}")
            time.sleep(2)  # Add 2 second delay to waste their time
        
        logger.info(f"[MAZE] {method} /{full_path} | Access: {access_level} | IP: {client_ip}")
        
        # Check if endpoint exists in state
        if state.endpoint_exists(full_path, method):
            endpoint_data = state.get_endpoint(full_path, method)
            response_json = endpoint_data['response_template']
            
            try:
                return jsonify(json.loads(response_json))
            except:
                return jsonify({"data": response_json})
        
        # NEW ENDPOINT - Log attacker details
        logger.warning(f"[MAZE] NEW endpoint: {method} /{full_path}")
        
        # DETAILED ATTACKER LOG
        attacker_info = {
            "event": "NEW_ENDPOINT_DISCOVERY",
            "timestamp": datetime.utcnow().isoformat(),
            "ip": client_ip,
            "user_agent": user_agent,
            "method": method,
            "endpoint": f"/{full_path}",
            "access_level": access_level,
            "has_auth": bool(authorization)
        }
        
        logger.critical(f"[ATTACKER] {json.dumps(attacker_info)}")
        print(f"\n{'='*60}")
        print(f"[NEW ENDPOINT DISCOVERED]")
        print(f"  IP:        {client_ip}")
        print(f"  Time:      {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  Endpoint:  {method} /{full_path}")
        print(f"  User-Agent: {user_agent[:50]}...")
        print(f"{'='*60}\n")
        
        # Handle unauthorized/forbidden cases
        if access_level == "unauthorized":
            response_data = {
                "error": "Unauthorized",
                "message": "Authentication required",
                "hint": "POST /api/v1/auth/login to obtain a token",
                "timestamp": datetime.utcnow().isoformat()
            }
            state.save_endpoint(full_path, method, json.dumps(response_data))
            return jsonify(response_data), 401
        
        elif access_level == "forbidden":
            response_data = {
                "error": "Forbidden",
                "message": "Insufficient permissions",
                "hint": "Request elevation at /api/v1/auth/elevate",
                "current_access": "user",
                "required_access": "admin",
                "timestamp": datetime.utcnow().isoformat()
            }
            state.save_endpoint(full_path, method, json.dumps(response_data))
            return jsonify(response_data), 403
        
        # Generate realistic response with LLM (with maze context)
        if llm_enabled and llm:
            try:
                # Use enhanced prompt with maze context
                enhanced_prompt = maze.enhance_prompt_with_context(full_path, method, access_level)
                response_content = llm.generate_api_response(full_path, method, context=enhanced_prompt)
                
                # Add breadcrumbs to the response
                response_data = json.loads(response_content)
                response_data = maze.add_breadcrumbs(response_data, full_path, access_level)
                
                # CONTEXTUAL FILE GENERATION
                # Randomly add files to certain endpoints (30% chance)
                if random.random() < 0.3 and method == "GET":
                    file_info = generate_contextual_file(full_path, client_ip)
                    if file_info:
                        response_data["_attachments"] = response_data.get("_attachments", [])
                        response_data["_attachments"].append({
                            "filename": file_info["filename"],
                            "type": file_info["type"],
                            "download_url": f"/api/download/{file_info['filename']}",
                            "size": file_info.get("size", "unknown"),
                            "description": file_info.get("description", "Related document")
                        })
                        logger.info(f"[FILE] Generated {file_info['type']} for /{full_path}")
                
                response_content = json.dumps(response_data)
                
                logger.info(f"[GEMINI+MAZE] Generated for {method} {full_path}")
                print(f"\n[GEMINI+MAZE] {method} {full_path} | Level: {access_level}")
                
            except Exception as e:
                logger.error(f"Gemini failed: {e}")
                response_content = generate_fallback_response(full_path, method)
                print(f"\n[FALLBACK] {method} {full_path}")
        else:
            response_content = generate_fallback_response(full_path, method)
        
        # Save endpoint
        state.save_endpoint(full_path, method, response_content)
        
        try:
            return jsonify(json.loads(response_content))
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return jsonify({"data": response_content})
            
    except Exception as e:
        logger.error(f"CRITICAL ERROR in dynamic_endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Internal Server Error", 
            "details": str(e)
        }), 500

def generate_fallback_response(path, method):
    """Fallback response when LLM fails"""
    if method == "GET":
        return json.dumps({
            "data": [],
            "message": "Success",
            "path": path,
            "timestamp": datetime.utcnow().isoformat()
        })
    elif method == "POST":
        return json.dumps({
            "id": fake.random_int(100, 9999),
            "status": "created",
            "message": "Resource created"
        })
    elif method == "PUT":
        return json.dumps({
            "id": fake.random_int(100, 9999),
            "status": "updated"
        })
    elif method == "DELETE":
        return json.dumps({
            "status": "deleted"
        })
    else:
        return json.dumps({"message": "Success"})

# Startup banner
def print_startup_banner():
    print("\n" + "="*60)
    print("[HONEYPOT] Dynamic API Honeypot with Maze System Started")
    print("="*60)
    print(f"[STATS] {state.get_statistics()}")
    print(f"[LLM] {'Enabled (Gemini)' if llm_enabled else 'Disabled (using fallbacks)'}")
    print(f"[MAZE] Realistic interconnected API structure")
    print(f"[LOGS] {log_dir.absolute()}/api_audit.log")
    print(f"[SERVER] http://localhost:8001")
    print("="*60 + "\n")

if __name__ == "__main__":
    print_startup_banner()
    app.run(host="0.0.0.0", port=8001, debug=True)
