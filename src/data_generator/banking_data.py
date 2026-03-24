"""
Dynamic Banking Data Generator
Generates random, realistic banking data for each API call
"""

import random
from datetime import datetime, timedelta
from faker import Faker
import uuid

fake = Faker()


class BankingDataGenerator:
    """Generate dynamic banking data that stays consistent during server session"""
    
    def __init__(self, llm_instance=None):
        self.llm = llm_instance
        self.company_prefixes = ["Apex", "Sterling", "Meridian", "Global", "Premier", "Atlas", "Pinnacle", "Summit", "Crown", "Elite", "Pacific", "Northern", "Eastern", "Western", "Central"]
        self.company_suffixes = ["Financial Holdings", "Capital Partners", "Trust Corp", "Banking Group", "Investment Services", "Asset Management", "Securities", "Wealth Management", "Credit Union", "Finance Co"]
        self.account_types = ["business", "corporate", "investment", "savings", "checking", "money_market", "treasury"]
        self.payment_methods = ["wire", "ach", "swift", "internal", "sepa", "fedwire"]
        self.currencies = ["USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD"]
        self.transaction_types = ["wire_transfer", "deposit", "withdrawal", "payment", "refund", "fee", "interest", "dividend", "payroll"]
        
        # SESSION CACHE - Data stays same on refresh, only changes on server restart
        self._cache = {}
    
    def _gen_id(self, prefix, length=9):
        """Generate random ID with prefix"""
        return f"{prefix}{random.randint(10**(length-1), 10**length - 1)}"
    
    def _gen_amount(self, min_val=100, max_val=1000000):
        """Generate random money amount"""
        return round(random.uniform(min_val, max_val), 2)
    
    def _gen_date(self, days_back=365):
        """Generate random date within range"""
        return (datetime.now() - timedelta(days=random.randint(0, days_back))).isoformat() + "Z"
    
    def _gen_company_name(self):
        """Generate random company name"""
        return f"{random.choice(self.company_prefixes)} {random.choice(self.company_suffixes)}"
    
    def generate_companies(self, count=None):
        """Generate list of companies - cached per session"""
        cache_key = 'companies'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if count is None:
            count = random.randint(8, 20)
        
        if self.llm:
            prompt = f"Generate a JSON array of {count} fake company records. Each record should have: 'id' (format: COMxxxxxx), 'name' (realistic corporate name), 'status' (active/pending/suspended), 'created' (ISO8601 date), 'accounts' (path: /companies/{{id}}/accounts), 'webhooks' (path: /companies/{{id}}/webhooks), 'apiCredentials' (path: /companies/{{id}}/apiCredentials). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    self._cache[cache_key] = data
                    return data
            except Exception:
                pass
                
        # Fallback
        companies = []
        for _ in range(count):
            cid = self._gen_id("COM", 6)
            companies.append({
                "id": cid,
                "name": self._gen_company_name(),
                "status": random.choice(["active", "active", "active", "pending", "suspended"]),
                "created": self._gen_date(1825),
                "accounts": f"/companies/{cid}/accounts",
                "webhooks": f"/companies/{cid}/webhooks",
                "apiCredentials": f"/companies/{cid}/apiCredentials"
            })
        
        self._cache[cache_key] = companies
        return companies
    
    def generate_accounts(self, count=None):
        """Generate list of accounts - cached per session"""
        cache_key = 'accounts'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if count is None:
            count = random.randint(15, 40)
        
        if self.llm:
            prompt = f"Generate a JSON array of {count} fake bank account records. Each should have: 'id' (format: ACCxxxxxxxxx), 'holder' (company name), 'type' (business/corporate/checking/savings), 'balance' (numeric float between 10k-50m), 'available' (numeric float), 'currency' (USD/EUR/GBP), 'opened' (ISO8601 date), 'status' (active/frozen/closed), 'details' (path: /api/v1/accounts/{{id}}), 'transactions' (path: /api/v1/accounts/{{id}}/transactions), 'statements' (path: /api/v1/accounts/{{id}}/statements). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    self._cache[cache_key] = data
                    return data
            except Exception:
                pass
                
        # Fallback
        accounts = []
        for _ in range(count):
            aid = self._gen_id("ACC", 9)
            accounts.append({
                "id": aid,
                "holder": self._gen_company_name(),
                "type": random.choice(self.account_types),
                "balance": self._gen_amount(10000, 50000000),
                "available": self._gen_amount(5000, 45000000),
                "currency": random.choice(self.currencies[:3]),
                "opened": self._gen_date(1825),
                "status": random.choice(["active", "active", "active", "frozen", "closed"]),
                "details": f"/api/v1/accounts/{aid}",
                "transactions": f"/api/v1/accounts/{aid}/transactions",
                "statements": f"/api/v1/accounts/{aid}/statements"
            })
        
        self._cache[cache_key] = accounts
        return accounts
    
    def generate_transactions(self, count=None, account_id=None):
        """Generate list of transactions - cached per session"""
        cache_key = f'transactions_{account_id or "all"}'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if count is None:
            count = random.randint(20, 100)
        
        if self.llm:
            prompt = f"Generate a JSON array of {count} fake bank transactions for account ID '{account_id or 'mixed accounts'}'. Each must have: 'id' (format: TXNxxxxxx), 'amount' (numeric float between -50k and 50k), 'type' (deposit/withdrawal/wire_transfer/payment), 'date' (ISO8601 string, sort by this), 'status' (completed/pending/failed), 'reference' (REFxxxxxx), 'details' (path: /api/v1/transactions/{{id}})"
            if not account_id:
                prompt += ", 'from_account' (ACCxxxx), 'to_account' (ACCxxxx)"
            prompt += ". Return ONLY the array."
            
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    result = sorted(data, key=lambda x: x.get("date", ""), reverse=True)
                    self._cache[cache_key] = result
                    return result
            except Exception:
                pass
                
        # Fallback
        transactions = []
        for _ in range(count):
            tid = self._gen_id("TXN", 10)
            amount = self._gen_amount(50, 500000)
            txn_type = random.choice(self.transaction_types)
            
            txn = {
                "id": tid,
                "amount": amount if txn_type in ["deposit", "interest", "dividend", "refund"] else -amount,
                "type": txn_type,
                "date": self._gen_date(90),
                "status": random.choice(["completed", "completed", "completed", "pending", "failed"]),
                "reference": f"REF{random.randint(100000, 999999)}",
                "details": f"/api/v1/transactions/{tid}"
            }
            
            if account_id:
                txn["account_id"] = account_id
            else:
                txn["from_account"] = self._gen_id("ACC", 9)
                txn["to_account"] = self._gen_id("ACC", 9)
            
            if txn_type == "wire_transfer":
                txn["swift_code"] = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=8))}"
            elif txn_type == "payroll":
                txn["batch"] = f"PAY_{datetime.now().strftime('%b').upper()}_{datetime.now().year}"
            
            transactions.append(txn)
        
        result = sorted(transactions, key=lambda x: x["date"], reverse=True)
        self._cache[cache_key] = result
        return result
    
    def generate_payments(self, count=None):
        """Generate list of payments - cached per session"""
        cache_key = 'payments'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if count is None:
            count = random.randint(10, 35)
        
        if self.llm:
            prompt = f"Generate a JSON array of {count} fake bank payments. Each must have: 'id' (format: PAYxxxxxx), 'amount' (numeric float), 'currency' (USD/EUR/GBP/CHF), 'method' (wire/ach/swift/internal), 'status' (completed/pending/processing/failed), 'created' (ISO8601 date), 'from_account' (ACCxxxx), 'to_account' (ACCxxxx), 'details' (path: /api/v1/payments/{{id}}), 'receipt' (path: /api/download/payment_receipt_{{id}}.pdf). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    self._cache[cache_key] = data
                    return data
            except Exception:
                pass
                
        # Fallback
        payments = []
        for _ in range(count):
            pid = self._gen_id("PAY", 9)
            payments.append({
                "id": pid,
                "amount": self._gen_amount(100, 250000),
                "currency": random.choice(self.currencies[:4]),
                "method": random.choice(self.payment_methods),
                "status": random.choice(["completed", "completed", "pending", "processing", "failed"]),
                "created": self._gen_date(30),
                "from_account": self._gen_id("ACC", 9),
                "to_account": self._gen_id("ACC", 9),
                "details": f"/api/v1/payments/{pid}",
                "receipt": f"/api/download/payment_receipt_{pid}.pdf"
            })
        
        self._cache[cache_key] = payments
        return payments
    
    def generate_merchants(self, count=None):
        """Generate list of merchants - cached per session"""
        cache_key = 'merchants'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if count is None:
            count = random.randint(8, 25)
        
        if self.llm:
            prompt = f"Generate a JSON array of {count} fake merchants. Each must have: 'id' (format: MCHxxxxxxx), 'name' (realistic business name), 'status' (active/suspended/pending), 'created' (ISO8601 date), 'mcc' (4 digit code), 'terminals' (path: /merchants/{{id}}/terminals), 'transactions' (path: /merchants/{{id}}/transactions), 'settlements' (path: /merchants/{{id}}/settlements). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    self._cache[cache_key] = data
                    return data
            except Exception:
                pass
                
        # Fallback
        merchant_types = ["Retail", "Restaurant", "E-commerce", "Services", "Healthcare", "Travel", "Entertainment"]
        merchants = []
        for _ in range(count):
            mid = self._gen_id("MCH", 7)
            merchants.append({
                "id": mid,
                "name": f"{fake.company()} {random.choice(merchant_types)}",
                "status": random.choice(["active", "active", "active", "suspended", "pending"]),
                "created": self._gen_date(730),
                "mcc": str(random.randint(1000, 9999)),
                "terminals": f"/merchants/{mid}/terminals",
                "transactions": f"/merchants/{mid}/transactions",
                "settlements": f"/merchants/{mid}/settlements"
            })
        
        self._cache[cache_key] = merchants
        return merchants
    
    def generate_terminals(self, merchant_id, count=None):
        """Generate list of terminals for a merchant"""
        if count is None:
            count = random.randint(3, 15)
        
        if self.llm:
            prompt = f"Generate a JSON array of {count} fake point-of-sale terminals for merchant '{merchant_id}'. Each must have: 'id' (format: TRMxxxxxx), 'model' (e.g. VX520, Lane3000), 'status' (online/offline/maintenance), 'serial' (SN followed by 12 hex chars), 'last_transaction' (ISO8601 date), 'config' (path: /api/download/terminal_{{id}}_config.js), 'logs' (path: /api/download/terminal_{{id}}_logs.txt). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception:
                pass
                
        # Fallback
        models = ["VX520", "VX680", "Lane3000", "P400", "M400", "Ingenico Move5000", "PAX A920"]
        terminals = []
        for i in range(count):
            tid = f"TRM{random.randint(100000, 999999)}"
            terminals.append({
                "id": tid,
                "model": random.choice(models),
                "status": random.choice(["online", "online", "online", "offline", "maintenance"]),
                "serial": f"SN{uuid.uuid4().hex[:12].upper()}",
                "last_transaction": self._gen_date(7),
                "config": f"/api/download/terminal_{tid}_config.js",
                "logs": f"/api/download/terminal_{tid}_logs.txt"
            })
        return terminals
    
    def generate_users(self, count=None):
        """Generate list of admin users - cached per session"""
        cache_key = 'users'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if count is None:
            count = random.randint(5, 15)
        
        if self.llm:
            prompt = f"Generate a JSON array of {count} fake bank employee/admin users. Each must have: 'id' (format: USRxxxxxx), 'name' (first last), 'email' (corporate email), 'role' (super_admin/admin/finance/support), 'last_login' (ISO8601 date), 'status' (active/locked), 'api_key' (path: /api/download/user_{{id}}_key.txt), 'permissions' (path: /api/v2/admin/users/{{id}}/permissions). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    self._cache[cache_key] = data
                    return data
            except Exception:
                pass
                
        # Fallback
        roles = ["super_admin", "admin", "finance_admin", "operations", "analyst", "support", "auditor"]
        users = []
        for _ in range(count):
            uid = self._gen_id("USR", 6)
            users.append({
                "id": uid,
                "name": fake.name(),
                "email": f"{fake.user_name()}@bank.internal",
                "role": random.choice(roles),
                "last_login": self._gen_date(30),
                "status": random.choice(["active", "active", "active", "inactive", "locked"]),
                "api_key": f"/api/download/user_{uid}_key.txt",
                "permissions": f"/api/v2/admin/users/{uid}/permissions"
            })
        
        self._cache[cache_key] = users
        return users
    
    def generate_reports(self):
        """Generate list of available reports - cached per session"""
        cache_key = 'reports'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if self.llm:
            prompt = f"Generate a JSON array of 15-20 fake downloadable banking reports and exports (PDFs, CSVs, JSONs, SQLite DBs). Each must have: 'name' (filename ending in .pdf/.csv/.json/.db/etc), 'type' (the extension Without dot), 'size' (e.g. '2.4 MB', '450 KB'), 'created' (ISO8601 date), 'download' (path: /api/download/{{name}}). Ensure filenames look like sensitive corporate exports (Q4_financials, audit_trail, customer_db, backup). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    self._cache[cache_key] = data
                    return data
            except Exception:
                pass
                
        # Fallback
        report_types = [
            ("Q4_2024_Financial", "pdf", "2.4 MB"),
            ("Annual_Report_2024", "pdf", "8.1 MB"),
            ("Monthly_Statement", "pdf", "1.2 MB"),
            ("transactions_export", "csv", "15.4 MB"),
            ("transactions_full", "sqlite", "142 MB"),
            ("customer_data", "db", "89 MB"),
            ("audit_trail", "json", "28 MB"),
            ("access_logs", "xml", "12 MB"),
            ("payment_config", "json", "450 KB"),
            ("webhook_secrets", "xml", "128 KB"),
            ("terminal_configs", "js", "890 KB"),
            ("compliance_report", "pdf", "3.2 MB"),
            ("security_events", "db", "45 MB"),
            ("daily_summary", "csv", "890 KB"),
        ]
        
        reports = []
        for name, ext, size in report_types:
            # Add random date suffix to some
            if random.random() > 0.3:
                date_suffix = f"_{datetime.now().strftime('%Y_%m')}"
            else:
                date_suffix = ""
            
            filename = f"{name}{date_suffix}.{ext}"
            reports.append({
                "name": filename,
                "type": ext,
                "size": size,
                "created": self._gen_date(90),
                "download": f"/api/download/{filename}"
            })
        
        # Add some random extra reports
        for _ in range(random.randint(3, 8)):
            ext = random.choice(["pdf", "csv", "xlsx", "json", "xml", "db"])
            name = f"{random.choice(['export', 'backup', 'report', 'data', 'log'])}_{uuid.uuid4().hex[:8]}"
            reports.append({
                "name": f"{name}.{ext}",
                "type": ext,
                "size": f"{random.randint(100, 9999)} KB",
                "created": self._gen_date(30),
                "download": f"/api/download/{name}.{ext}"
            })
        
        self._cache[cache_key] = reports
        return reports
    
    def generate_backups(self, count=None):
        """Generate list of backup files - cached per session"""
        cache_key = 'backups'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if count is None:
            count = random.randint(5, 12)
        
        if self.llm:
            prompt = f"Generate a JSON array of {count} fake database/server backups. Each must have: 'name' (filename ending in .db/.sqlite/.tar.gz/.zip), 'type' (full/incremental/differential), 'size' (e.g. '1.2 GB', '450 MB'), 'created' (ISO8601 date), 'download' (path: /api/download/{{name}}). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    self._cache[cache_key] = data
                    return data
            except Exception:
                pass
                
        # Fallback
        backups = []
        for i in range(count):
            date = datetime.now() - timedelta(days=i * random.randint(1, 7))
            backup_type = random.choice(["full", "incremental", "differential"])
            ext = random.choice(["db", "sqlite", "tar.gz", "zip"])
            name = f"{backup_type}_backup_{date.strftime('%Y_%m_%d')}"
            size = f"{random.randint(100, 9999)} MB" if backup_type == "full" else f"{random.randint(10, 500)} MB"
            
            backups.append({
                "name": f"{name}.{ext}",
                "type": backup_type,
                "size": size,
                "created": date.isoformat() + "Z",
                "download": f"/api/download/{name}.{ext}"
            })
        
        self._cache[cache_key] = backups
        return backups
    
    def generate_secrets(self):
        """Generate list of secrets (high-value targets)"""
        if self.llm:
            prompt = f"Generate a JSON array of highly sensitive fake secrets/credentials files (e.g. master keys, database passwords, env files, certs). Each must have: 'name' (secret logical name), 'type' (api_key/encryption/database/webhook), 'download' (path: /api/download/{{filename}}). Return ONLY the array."
            try:
                data = self.llm.generate_structured_data(prompt, "json")
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception:
                pass
                
        # Fallback
        secrets = [
            {"name": "api_master_key", "type": "api_key", "download": "/api/download/master_api_key.txt"},
            {"name": "encryption_keys", "type": "encryption", "download": "/api/download/encryption_keys.json"},
            {"name": "webhook_secrets", "type": "webhook", "download": "/api/download/webhook_secrets.xml"},
            {"name": "database_credentials", "type": "database", "download": "/api/download/database_credentials.txt"},
            {"name": "ssl_certificates", "type": "certificate", "download": "/api/download/ssl_certs.zip"},
            {"name": "oauth_tokens", "type": "oauth", "download": "/api/download/oauth_tokens.json"},
            {"name": "service_accounts", "type": "service", "download": "/api/download/service_accounts.json"},
        ]
        
        # Add random environment-specific secrets
        for env in ["prod", "staging", "dev"]:
            secrets.append({
                "name": f"{env}_credentials",
                "type": "environment",
                "download": f"/api/download/{env}_credentials.txt"
            })
        
        return secrets


# Global instance
banking_data = BankingDataGenerator()
