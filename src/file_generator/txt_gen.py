"""Text File Generator for Honeypot Bait Files"""

import random
from pathlib import Path
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

class TextFileGenerator:
    """Generates realistic text files (logs, configs, credentials)"""
    
    def __init__(self, output_dir="generated_files/textfiles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_text_file(self, context, beacon_id, endpoint_path="/api/config"):
        """Generate text file based on endpoint context"""
        
        # Determine file type from endpoint
        file_type = self._infer_file_type(endpoint_path)
        
        if file_type == "env":
            return self._generate_env_file(context, beacon_id)
        elif file_type == "log":
            return self._generate_log_file(context, beacon_id)
        elif file_type == "config":
            return self._generate_config_file(context, beacon_id)
        elif file_type == "credentials":
            return self._generate_credentials_file(context, beacon_id)
        else:
            return self._generate_generic_file(context, beacon_id)
    
    def _infer_file_type(self, endpoint):
        """Determine file type from endpoint path"""
        endpoint_lower = endpoint.lower()
        
        if 'env' in endpoint_lower or 'environment' in endpoint_lower:
            return 'env'
        elif 'log' in endpoint_lower or 'audit' in endpoint_lower:
            return 'log'
        elif 'config' in endpoint_lower or 'settings' in endpoint_lower:
            return 'config'
        elif 'cred' in endpoint_lower or 'secret' in endpoint_lower or 'key' in endpoint_lower:
            return 'credentials'
        else:
            return 'generic'
    
    def _generate_env_file(self, context, beacon_id):
        """Generate .env configuration file"""
        filename = f"production_{random.choice(['v1', 'v2', 'main', 'prod'])}.env"
        filepath = self.output_dir / filename
        
        content = f"""# Production Environment Configuration
# Generated: {datetime.utcnow().isoformat()}
# DO NOT COMMIT TO VERSION CONTROL

# Database Configuration
DB_HOST=db-prod-{random.randint(1, 9)}.internal.securebank.com
DB_PORT=5432
DB_NAME=banking_prod
DB_USER=admin_user
DB_PASSWORD={fake.password(length=16, special_chars=True)}

# API Keys
API_KEY={fake.sha256()[:32]}
SECRET_KEY={fake.sha256()[:64]}
JWT_SECRET={fake.sha256()[:48]}

# Third-Party Services
STRIPE_API_KEY=sk_live_{fake.sha256()[:32]}
SENDGRID_API_KEY=SG.{fake.sha256()[:48]}
AWS_ACCESS_KEY_ID=AKIA{fake.sha256()[:16].upper()}
AWS_SECRET_ACCESS_KEY={fake.sha256()[:40]}

# Redis
REDIS_HOST=cache-{random.randint(1, 5)}.internal.securebank.com
REDIS_PORT=6379
REDIS_PASSWORD={fake.password(length=20)}

# Application Settings
APP_ENV=production
DEBUG=false
LOG_LEVEL=info
PORT=8080

# Security
ENCRYPTION_KEY={fake.sha256()[:32]}
SESSION_SECRET={fake.sha256()[:48]}

# Monitoring
SENTRY_DSN=https://{fake.sha256()[:32]}@sentry.io/{random.randint(1000000, 9999999)}

# Beacon (hidden)  
TRACKING_ID={beacon_id}
"""
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"[TXT] Generated {filename} ({filepath.stat().st_size} bytes)")
        return filepath, filename
    
    def _generate_log_file(self, context, beacon_id):
        """Generate system/audit log file"""
        filename = f"system_audit_{datetime.now().strftime('%Y%m%d')}.log"
        filepath = self.output_dir / filename
        
        lines = []
        lines.append(f"# System Audit Log - Generated {datetime.utcnow().isoformat()}")
        lines.append(f"# Tracking: {beacon_id}\n")
        
        # Generate log entries
        for _ in range(random.randint(100, 500)):
            timestamp = fake.date_time_between(start_date='-7d', end_date='now')
            level = random.choice(['INFO', 'WARNING', 'ERROR', 'DEBUG'])
            user = f"user_{random.randint(100, 999)}"
            ip = fake.ipv4()
            action = random.choice([
                'LOGIN_SUCCESS', 'LOGIN_FAILED', 'API_CALL', 'DATA_ACCESS',
                'FILE_DOWNLOAD', 'CONFIG_CHANGE', 'PERMISSION_DENIED'
            ])
            
            lines.append(f"{timestamp.isoformat()} [{level}] {user}@{ip} - {action} - {fake.sentence()}")
        
        content = '\n'.join(lines)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"[TXT] Generated {filename} ({filepath.stat().st_size} bytes)")
        return filepath, filename
    
    def _generate_config_file(self, context, beacon_id):
        """Generate application config file"""
        filename = f"app_config_{random.choice(['prod', 'staging', 'main'])}.conf"
        filepath = self.output_dir / filename
        
        content = f"""# Application Configuration File
# Last Modified: {datetime.utcnow().isoformat()}
# Beacon: {beacon_id}

[database]
host = db-primary.internal.securebank.com
port = 5432
database = banking_main
username = app_user
password = {fake.password(length=16)}
max_connections = 100
timeout = 30

[api]
base_url = https://api.securebank.com/v2
timeout = 10
retry_attempts = 3
api_key = {fake.sha256()[:32]}

[security]
encryption_algorithm = AES-256-GCM
hashing_algorithm = SHA-256
session_timeout = 3600
max_login_attempts = 5

[logging]
level = INFO
file = /var/log/banking/app.log
max_size = 100MB
retention_days = 90

[cache]
type = redis
host = {fake.ipv4_private()}
port = 6379
ttl = 3600

[monitoring]
enabled = true
endpoint = https://metrics.securebank.com/api/v1/ingest
api_key = {fake.sha256()[:24]}
"""
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"[TXT] Generated {filename} ({filepath.stat().st_size} bytes)")
        return filepath, filename
    
    def _generate_credentials_file(self, context, beacon_id):
        """Generate credentials/secrets file"""
        filename = f"secrets_{random.choice(['backup', 'vault', 'master'])}.txt"
        filepath = self.output_dir / filename
        
        content = f"""SENSITIVE CREDENTIALS - RESTRICTED ACCESS
Generated: {datetime.utcnow().isoformat()}
Classification: CONFIDENTIAL
Tracking: {beacon_id}

=== Database Credentials ===
Production DB:
  Host: db-prod-1.internal.securebank.com
  Username: db_admin
  Password: {fake.password(length=20, special_chars=True)}

Read Replica:
  Host: db-replica-1.internal.securebank.com
  Username: readonly_user
  Password: {fake.password(length=16)}

=== API Keys ===
Stripe Production: sk_live_{fake.sha256()[:32]}
Plaid API: {fake.sha256()[:48]}
Twilio Account SID: AC{fake.sha256()[:32]}
Twilio Auth Token: {fake.sha256()[:32]}

=== AWS Credentials ===
Access Key ID: AKIA{fake.sha256()[:16].upper()}
Secret Access Key: {fake.sha256()[:40]}
Region: us-east-1

=== SSH Keys ===
Production Server: root@prod-{random.randint(1, 5)}.securebank.com
Private Key: /root/.ssh/id_rsa_prod
Passphrase: {fake.password(length=24)}

=== Admin Accounts ===
Super Admin:
  Username: sa_admin
  Password: {fake.password(length=20, special_chars=True)}
  
System Admin:
  Username: sys_admin
  Password: {fake.password(length=18, special_chars=True)}

=== Encryption Keys ===
Master Key: {fake.sha256()}
Backup Key: {fake.sha256()}

--- END OF DOCUMENT ---
"""
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"[TXT] Generated {filename} ({filepath.stat().st_size} bytes)")
        return filepath, filename
    
    def _generate_generic_file(self, context, beacon_id):
        """Generate generic data file"""
        filename = f"data_export_{datetime.now().strftime('%Y%m%d')}.txt"
        filepath = self.output_dir / filename
        
        content = f"""Data Export Report
Generated: {datetime.utcnow().isoformat()}
Export ID: {beacon_id}

{fake.text(max_nb_chars=1000)}

Statistics:
- Total Records: {random.randint(1000, 50000)}
- Date Range: {fake.date_between(start_date='-1y')} to {datetime.now().date()}
- Format: Plain Text
- Compression: None

{fake.text(max_nb_chars=500)}
"""
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"[TXT] Generated {filename} ({filepath.stat().st_size} bytes)")
        return filepath, filename
