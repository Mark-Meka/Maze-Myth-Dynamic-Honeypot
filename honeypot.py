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
from src.api_generator.http_responses import HTTPResponseGenerator
from src.rag import RAGLoader
from src.data_generator import banking_data

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
http_resp = HTTPResponseGenerator()  # HTTP Response Generator

# Load RAG banking context
try:
    rag = RAGLoader(rag_dir="src/rag")
    rag_enabled = True
    print("[RAG] Banking API context loaded")
except Exception as e:
    print(f"[RAG] Load Failed: {e}")
    rag = None
    rag_enabled = False


try:
    llm = LLMGenerator()
    llm_enabled = True
    print("[MAZE] Gemini AI enabled for realistic banking responses")
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

# CRITICAL: Ensure console handler is attached to logger (Flask may override)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# ===== SPECIFIC ROUTES (these have priority) =====

@app.route("/")
def root():
    company_name = rag.get_company_name() if rag_enabled else "SecureBank Financial Services"
    return jsonify({
        "name": f"{company_name} API Gateway",
        "version": "3.2.0",
        "status": "operational",
        "api": {
            "companies": "/companies",
            "merchants": "/merchants", 
            "accounts": "/api/v1/accounts",
            "transactions": "/api/v1/transactions",
            "payments": "/api/v1/payments",
            "reports": "/api/v1/reports",
            "admin": "/api/v2/admin",
            "internal": "/internal"
        },
        "auth": "/api/v1/auth/login"
    })

# ===== REAL BANKING DATA ENDPOINTS (DYNAMIC) =====

@app.route("/companies")
def list_companies():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /companies from {client_ip}")
    companies = banking_data.generate_companies()
    return jsonify({
        "companies": companies,
        "total": len(companies),
        "_links": {"webhooks": f"/companies/{companies[0]['id']}/webhooks" if companies else None}
    })

@app.route("/companies/<company_id>")
def get_company(company_id):
    client_ip = request.remote_addr
    logger.info(f"[API] GET /companies/{company_id} from {client_ip}")
    return jsonify({
        "id": company_id,
        "name": banking_data._gen_company_name(),
        "status": "active",
        "created": banking_data._gen_date(1825),
        "accounts": f"/companies/{company_id}/accounts",
        "webhooks": f"/companies/{company_id}/webhooks",
        "apiCredentials": f"/companies/{company_id}/apiCredentials",
        "settings": f"/companies/{company_id}/settings"
    })

@app.route("/companies/<company_id>/accounts")
def company_accounts(company_id):
    client_ip = request.remote_addr
    logger.info(f"[API] GET /companies/{company_id}/accounts from {client_ip}")
    accounts = banking_data.generate_accounts(random.randint(5, 15))
    return jsonify({
        "company_id": company_id,
        "accounts": accounts,
        "total": len(accounts)
    })

@app.route("/companies/<company_id>/apiCredentials")
def company_credentials(company_id):
    client_ip = request.remote_addr
    logger.critical(f"[ALERT] API credentials accessed by {client_ip}")
    creds = []
    for i in range(random.randint(3, 8)):
        cred_id = f"cred_{random.randint(1000000000, 9999999999)}"
        creds.append({
            "id": cred_id,
            "type": random.choice(["api_key", "webhook_secret", "oauth_token", "service_key"]),
            "created": banking_data._gen_date(365),
            "download": f"/api/download/{cred_id}_key.json"
        })
    return jsonify({"credentials": creds, "total": len(creds)})

@app.route("/api/v1/accounts")
def list_accounts():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /api/v1/accounts from {client_ip}")
    accounts = banking_data.generate_accounts()
    return jsonify({
        "accounts": accounts,
        "total": len(accounts),
        "export": "/api/v1/accounts/export"
    })

@app.route("/api/v1/accounts/<account_id>")
def get_account(account_id):
    client_ip = request.remote_addr
    logger.info(f"[API] GET /api/v1/accounts/{account_id} from {client_ip}")
    return jsonify({
        "id": account_id,
        "holder": banking_data._gen_company_name(),
        "type": random.choice(["business", "corporate", "investment", "savings"]),
        "balance": banking_data._gen_amount(10000, 50000000),
        "available": banking_data._gen_amount(5000, 45000000),
        "currency": random.choice(["USD", "EUR", "GBP"]),
        "opened": banking_data._gen_date(1825),
        "transactions": f"/api/v1/accounts/{account_id}/transactions",
        "statements": f"/api/v1/accounts/{account_id}/statements",
        "transfers": f"/api/v1/accounts/{account_id}/transfers"
    })

@app.route("/api/v1/accounts/<account_id>/transactions")
def account_transactions(account_id):
    client_ip = request.remote_addr
    logger.info(f"[API] GET transactions for {account_id} from {client_ip}")
    transactions = banking_data.generate_transactions(account_id=account_id)
    return jsonify({
        "account_id": account_id,
        "transactions": transactions,
        "total": len(transactions),
        "export": f"/api/v1/accounts/{account_id}/transactions/export"
    })

@app.route("/api/v1/accounts/<account_id>/statements")
def account_statements(account_id):
    client_ip = request.remote_addr
    logger.info(f"[API] GET statements for {account_id} from {client_ip}")
    statements = []
    for i in range(random.randint(6, 24)):
        date = datetime.now() - timedelta(days=i * 30)
        period = date.strftime("%Y-%m")
        statements.append({
            "period": period,
            "file": f"/api/download/statement_{account_id}_{period.replace('-', '_')}.pdf"
        })
    return jsonify({
        "account_id": account_id,
        "statements": statements,
        "export_all": f"/api/download/statements_{account_id}_all.zip"
    })

@app.route("/api/v1/transactions")
def list_transactions():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /api/v1/transactions from {client_ip}")
    transactions = banking_data.generate_transactions()
    return jsonify({
        "transactions": transactions,
        "total": len(transactions),
        "export": "/api/v1/transactions/export",
        "reports": "/api/v1/reports/transactions"
    })

@app.route("/api/v1/payments")
def list_payments():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /api/v1/payments from {client_ip}")
    payments = banking_data.generate_payments()
    return jsonify({
        "payments": payments,
        "total": len(payments)
    })

@app.route("/merchants")
def list_merchants():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /merchants from {client_ip}")
    merchants = banking_data.generate_merchants()
    return jsonify({
        "merchants": merchants,
        "total": len(merchants)
    })

@app.route("/merchants/<merchant_id>/terminals")
def merchant_terminals(merchant_id):
    client_ip = request.remote_addr
    logger.info(f"[API] GET terminals for {merchant_id} from {client_ip}")
    terminals = banking_data.generate_terminals(merchant_id)
    return jsonify({
        "merchant_id": merchant_id,
        "terminals": terminals,
        "total": len(terminals)
    })

@app.route("/api/v1/reports")
def list_reports():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /api/v1/reports from {client_ip}")
    reports = banking_data.generate_reports()
    return jsonify({
        "reports": {
            "financial": "/api/v1/reports/financial",
            "transactions": "/api/v1/reports/transactions",
            "audit": "/api/v1/reports/audit",
            "compliance": "/api/v1/reports/compliance"
        },
        "recent_exports": reports,
        "total": len(reports)
    })

@app.route("/api/v1/reports/financial")
def financial_reports():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /api/v1/reports/financial from {client_ip}")
    reports = [r for r in banking_data.generate_reports() if r['type'] in ['pdf', 'xlsx', 'csv']]
    return jsonify({"reports": reports, "total": len(reports)})

@app.route("/api/v1/reports/transactions")  
def transaction_reports():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /api/v1/reports/transactions from {client_ip}")
    reports = [r for r in banking_data.generate_reports() if r['type'] in ['db', 'sqlite', 'csv', 'xml']]
    return jsonify({"reports": reports, "total": len(reports)})

@app.route("/api/v1/reports/audit")
def audit_reports():
    client_ip = request.remote_addr
    logger.info(f"[API] GET /api/v1/reports/audit from {client_ip}")
    reports = [r for r in banking_data.generate_reports() if r['type'] in ['json', 'xml', 'db', 'pdf']]
    return jsonify({"reports": reports, "total": len(reports)})

@app.route("/internal")
def internal_root():
    client_ip = request.remote_addr
    logger.warning(f"[ALERT] Internal endpoint accessed by {client_ip}")
    return jsonify({
        "debug": "/internal/debug",
        "config": "/internal/config",
        "deploy": "/internal/deploy",
        "backups": "/internal/backups",
        "logs": "/internal/logs"
    })

@app.route("/internal/config")
def internal_config():
    client_ip = request.remote_addr
    logger.critical(f"[ALERT] Internal config accessed by {client_ip}")
    return jsonify({
        "database": "/internal/config/database",
        "credentials": "/internal/config/credentials",
        "environment": "/internal/config/environment",
        "secrets": "/internal/config/secrets",
        "services": "/internal/config/services"
    })

@app.route("/internal/config/database")
def internal_database():
    client_ip = request.remote_addr
    logger.critical(f"[ALERT] Database config accessed by {client_ip}")
    import uuid
    return jsonify({
        "primary": {"host": f"db-primary-{random.randint(1,9)}.internal.bank", "port": 5432, "name": "banking_prod"},
        "replica": {"host": f"db-replica-{random.randint(1,5)}.internal.bank", "port": 5432, "name": "banking_prod"},
        "analytics": {"host": f"db-analytics.internal.bank", "port": 5432, "name": "analytics_warehouse"},
        "connection_string": "/api/download/db_connection.txt",
        "schema": "/api/download/schema.sql",
        "credentials": f"/api/download/db_creds_{uuid.uuid4().hex[:8]}.json"
    })

@app.route("/internal/backups")
def internal_backups():
    client_ip = request.remote_addr
    logger.critical(f"[ALERT] Backups accessed by {client_ip}")
    backups = banking_data.generate_backups()
    return jsonify({
        "backups": backups,
        "total": len(backups),
        "next_scheduled": banking_data._gen_date(0)
    })

@app.route("/api/v2/admin")
def admin_root():
    client_ip = request.remote_addr
    authorization = request.headers.get('Authorization')
    if not authorization:
        return jsonify({"error": "Unauthorized", "login": "/api/v1/auth/login"}), 401
    logger.warning(f"[ADMIN] Admin access by {client_ip}")
    return jsonify({
        "users": "/api/v2/admin/users",
        "settings": "/api/v2/admin/settings",
        "logs": "/api/v2/admin/logs",
        "secrets": "/api/v2/admin/secrets",
        "audit": "/api/v2/admin/audit"
    })

@app.route("/api/v2/admin/users")
def admin_users():
    client_ip = request.remote_addr
    logger.warning(f"[ADMIN] User list accessed by {client_ip}")
    users = banking_data.generate_users()
    return jsonify({
        "users": users,
        "total": len(users)
    })

@app.route("/api/v2/admin/secrets")
def admin_secrets():
    client_ip = request.remote_addr
    logger.critical(f"[CRITICAL] Admin secrets accessed by {client_ip}")
    secrets = banking_data.generate_secrets()
    return jsonify({
        "secrets": secrets,
        "total": len(secrets),
        "warning": "Audit logged"
    })

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
    """Universal file download with tracking"""
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    # LOG DOWNLOAD EVENT FOR DASHBOARD
    download_event = {
        "event": "FILE_DOWNLOAD",
        "timestamp": datetime.utcnow().isoformat(),
        "ip": client_ip,
        "filename": filename,
        "user_agent": user_agent[:100]
    }
    logger.critical(json.dumps(download_event))
    
    # Save to state for dashboard monitoring
    state.log_download(filename, client_ip, user_agent)
    
    try:
        import uuid
        beacon_id = str(uuid.uuid4())
        
        # PDF Files
        if filename.endswith('.pdf'):
            filepath, beacon_id = file_gen.generate_pdf(filename, client_ip)
            file_type = "pdf"
        
        # Excel Files
        elif filename.endswith(('.xlsx', '.xls')):
            filepath, beacon_id = file_gen.generate_excel(filename, client_ip)
            file_type = "excel"
        
        # SQLite/Database Files
        elif filename.endswith(('.db', '.sqlite', '.sqlite3')):
            from src.file_generator.sqlite_gen import SQLiteGenerator
            sqlite_gen = SQLiteGenerator()
            filepath, _ = sqlite_gen.generate_database({"ip": client_ip}, beacon_id, endpoint_path=f"/api/download/{filename}")
            file_type = "sqlite"
        
        # Text Files
        elif filename.endswith('.txt'):
            from src.file_generator.txt_gen import TextFileGenerator
            txt_gen = TextFileGenerator()
            filepath, _ = txt_gen.generate_text_file({"ip": client_ip}, beacon_id, endpoint_path=f"/api/download/{filename}")
            file_type = "txt"
        
        # XML Files
        elif filename.endswith('.xml'):
            from src.file_generator.multi_format_gen import MultiFormatGenerator
            multi_gen = MultiFormatGenerator()
            filepath, beacon_id = multi_gen.generate_xml(filename, client_ip)
            file_type = "xml"
        
        # CSV Files
        elif filename.endswith('.csv'):
            from src.file_generator.multi_format_gen import MultiFormatGenerator
            multi_gen = MultiFormatGenerator()
            filepath, beacon_id = multi_gen.generate_csv(filename, client_ip)
            file_type = "csv"
        
        # JavaScript Config Files
        elif filename.endswith('.js'):
            from src.file_generator.multi_format_gen import MultiFormatGenerator
            multi_gen = MultiFormatGenerator()
            filepath, beacon_id = multi_gen.generate_js(filename, client_ip)
            file_type = "js"
        
        # JSON Files
        elif filename.endswith('.json'):
            from src.file_generator.multi_format_gen import MultiFormatGenerator
            multi_gen = MultiFormatGenerator()
            filepath, beacon_id = multi_gen.generate_json(filename, client_ip)
            file_type = "json"
        
        # SQL Schema Files
        elif filename.endswith('.sql'):
            from src.file_generator.txt_gen import TextFileGenerator
            txt_gen = TextFileGenerator()
            filepath, _ = txt_gen.generate_text_file({"ip": client_ip, "type": "schema"}, beacon_id, endpoint_path="/internal/config/database")
            file_type = "sql"
        
        else:
            logger.warning(f"[DOWNLOAD] Unknown file type: {filename}")
            return jsonify({"error": "File not found"}), 404
        
        # Save beacon for tracking
        state.save_beacon(beacon_id, file_type, filename, client_ip)
        
        # Alert for sensitive files
        if any(x in filename.lower() for x in ['credential', 'secret', 'key', 'password', 'backup', 'config']):
            logger.critical(f"[CRITICAL] SENSITIVE FILE DOWNLOADED: {filename} by {client_ip}")
        
        print(f"\n{'='*60}")
        print(f"[FILE DOWNLOAD]")
        print(f"  File:    {filename}")
        print(f"  Type:    {file_type}")
        print(f"  IP:      {client_ip}")
        print(f"  Beacon:  {beacon_id[:8]}...")
        print(f"  Time:    {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*60}\n")
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"File generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal error", "message": str(e)}), 500


# ===== REPORT EXPORT ENDPOINTS (Generate Real Files) =====

@app.route("/api/v1/reports/export")
def export_reports():
    """Generate downloadable report files"""
    client_ip = request.remote_addr
    format_type = request.args.get('format', 'pdf')
    
    logger.warning(f"[EXPORT] Report export request: format={format_type} from {client_ip}")
    
    try:
        if format_type == 'pdf':
            filepath, beacon_id = file_gen.generate_pdf("financial_report.pdf", client_ip)
            filename = "financial_report.pdf"
        elif format_type == 'xlsx':
            filepath, beacon_id = file_gen.generate_excel("transactions.xlsx", client_ip)
            filename = "transactions.xlsx"
        elif format_type in ['sqlite', 'db']:
            from src.file_generator.sqlite_gen import SQLiteGenerator
            import uuid
            sqlite_gen = SQLiteGenerator()
            beacon_id = str(uuid.uuid4())
            filepath, filename = sqlite_gen.generate_database({"ip": client_ip}, beacon_id, endpoint_path="/api/v1/reports/export")
        elif format_type == 'txt':
            from src.file_generator.txt_gen import TextFileGenerator
            import uuid
            txt_gen = TextFileGenerator()
            beacon_id = str(uuid.uuid4())
            filepath, filename = txt_gen.generate_text_file({"ip": client_ip}, beacon_id, endpoint_path="/api/v1/reports/audit")
        else:
            return jsonify({"error": "Unsupported format", "supported": ["pdf", "xlsx", "sqlite", "db", "txt"]}), 400
        
        state.save_beacon(beacon_id, format_type, filename, client_ip)
        logger.critical(f"[EXPORT] File generated: {filename} for {client_ip}")
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({"error": "Export failed", "message": str(e)}), 500

@app.route("/api/v1/transactions/export")
def export_transactions():
    """Export transactions as downloadable file"""
    client_ip = request.remote_addr
    format_type = request.args.get('format', 'sqlite')
    
    logger.warning(f"[EXPORT] Transaction export: format={format_type} from {client_ip}")
    
    try:
        from src.file_generator.sqlite_gen import SQLiteGenerator
        import uuid
        sqlite_gen = SQLiteGenerator()
        beacon_id = str(uuid.uuid4())
        filepath, filename = sqlite_gen.generate_database({"ip": client_ip}, beacon_id, endpoint_path="/api/v1/transactions/export")
        
        state.save_beacon(beacon_id, "sqlite", filename, client_ip)
        logger.critical(f"[EXPORT] Transaction DB downloaded by {client_ip}")
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Transaction export error: {e}")
        return jsonify({"error": "Export failed"}), 500

@app.route("/internal/config/credentials")
def internal_credentials():
    """Fake credentials file - highly attractive target"""
    client_ip = request.remote_addr
    
    logger.critical(f"[ALERT] Internal credentials accessed by {client_ip}!")
    
    try:
        from src.file_generator.txt_gen import TextFileGenerator
        import uuid
        txt_gen = TextFileGenerator()
        beacon_id = str(uuid.uuid4())
        filepath, filename = txt_gen.generate_text_file({"ip": client_ip}, beacon_id, endpoint_path="/internal/config/credentials")
        
        state.save_beacon(beacon_id, "credentials", filename, client_ip)
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({
            "error": "Access logged",
            "message": "Contact security team",
            "alert_sent": True
        }), 403


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
        
        # DEBUG: Print every request hitting catch-all
        is_valid = maze.is_valid_endpoint(full_path, user_agent)
        print(f"[DEBUG] /{full_path} | valid={is_valid}", flush=True)
        
        # Determine access level based on path and token
        access_level = maze.determine_access_level(full_path, authorization)
        
        # VALIDATE ENDPOINT - Return 404 for paths not in our defined structure
        if not is_valid:
            logger.warning(f"[MAZE] INVALID path rejected: /{full_path}")
            # CONSOLE MONITORING - Always visible
            print(f"[404] {method} /{full_path} | IP: {client_ip} | NOT FOUND", flush=True)
            return jsonify({
                "error": "Not Found",
                "message": f"The requested URL was not found on this server.",
                "path": f"/{full_path}"
            }), 404
        
        
        # Log directory scanning (detect gobuster, dirsearch, etc)
        if maze._is_directory_buster(user_agent, full_path):
            logger.info(f"[SCAN] Directory scan detected: {user_agent[:50]}")
            print(f"[SCAN] Scanner detected: {user_agent[:30]} accessing /{full_path}", flush=True)
        
        # CHECK IF SHOULD RETURN ERROR STATUS CODE
        has_auth = authorization is not None
        should_error, status_code = http_resp.should_return_error(
            f"/{full_path}", 
            has_auth=has_auth,
            auth_level=access_level
        )
        
        if should_error:
            error_response = http_resp.get_response_for_status(status_code, f"/{full_path}")
            if error_response:
                logger.info(f"[HTTP] {status_code} response for /{full_path} - {access_level} access")
                return jsonify(error_response['response']), error_response['status_code'], error_response.get('headers', {})

        
        logger.info(f"[MAZE] {method} /{full_path} | Access: {access_level} | IP: {client_ip}")
        # CONSOLE OUTPUT - Always visible (Flask logging can be unreliable)
        import sys
        print(f"[REQUEST] {method} /{full_path} | IP: {client_ip} | Access: {access_level}", flush=True)
        
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
                api_response = llm.generate_api_response(
                    full_path, 
                    method,
                    context=f"access_level: {access_level}",
                    rag_context=rag if rag_enabled else None
                )
            except Exception as e:
                logger.error(f"[LLM] Generation failed: {e}")
                api_response = json.dumps({"data": [], "message": "Success"})
        else:
            # Fallback without LLM
            api_response = json.dumps({
                "data": [],
                "message": "Success", 
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # AUTO-GENERATE AND ATTACH FILES (20% chance)
        attachments = []
        if random.random() < 0.2:
            try:
                filepath, filename, beacon_id, file_type = file_gen.generate_random_file(
                    f"/{full_path}",
                    client_ip,
                    rag_context=rag if rag_enabled else None
                )
                
                # Add download URL to response
                download_url = f"/download/{beacon_id}"
                attachments.append({
                    "filename": filename,
                    "type": file_type,
                    "download_url": download_url,
                    "size": f"{filepath.stat().st_size} bytes"
                })
                
                # Save beacon for tracking
                state.save_beacon(beacon_id, filename, client_ip, f"/{full_path}")
                logger.info(f"[FILE] Generated {file_type} file: {filename} for /{full_path}")
            except Exception as e:
                logger.error(f"[FILE] Generation failed: {e}")
        
        # Add attachments to response if generated
        if attachments:
            try:
                response_dict = json.loads(api_response)
                response_dict['_attachments'] = attachments
                api_response = json.dumps(response_dict)
            except:
                pass
        
        response_content = api_response

        
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
    # use_reloader=False so logs show in main console (not subprocess)
    app.run(host="0.0.0.0", port=8001, debug=True, use_reloader=False)
