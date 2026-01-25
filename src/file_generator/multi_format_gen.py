"""
Multi-Format File Generator for Honeypot
Generates XML, CSV, JS, JSON files with tracking beacons
"""

import random
from pathlib import Path
from datetime import datetime, timedelta
from faker import Faker
import uuid
import json

fake = Faker()


class MultiFormatGenerator:
    """Generate tracked bait files in various formats"""
    
    def __init__(self, output_dir="generated_files"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_xml(self, filename, client_ip, file_type="audit"):
        """Generate XML file with embedded beacon reference"""
        beacon_id = str(uuid.uuid4())
        filepath = self.output_dir / f"{beacon_id}.xml"
        
        if "audit" in filename.lower() or "log" in filename.lower():
            content = self._generate_audit_xml(beacon_id, client_ip)
        elif "config" in filename.lower() or "webhook" in filename.lower():
            content = self._generate_config_xml(beacon_id)
        elif "transaction" in filename.lower():
            content = self._generate_transaction_xml(beacon_id)
        else:
            content = self._generate_generic_xml(beacon_id)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath, beacon_id
    
    def _generate_audit_xml(self, beacon_id, client_ip):
        events = []
        for i in range(50):
            timestamp = (datetime.now() - timedelta(hours=random.randint(1, 720))).isoformat()
            event_type = random.choice(["LOGIN", "LOGOUT", "TRANSFER", "ACCESS", "MODIFY", "DELETE"])
            user = f"USR{random.randint(100000, 999999)}"
            ip = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
            events.append(f'''    <event id="{i+1}">
        <timestamp>{timestamp}</timestamp>
        <type>{event_type}</type>
        <user>{user}</user>
        <ip>{ip}</ip>
        <resource>/api/v1/accounts/ACC{random.randint(100000000, 999999999)}</resource>
        <status>SUCCESS</status>
    </event>''')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Document ID: {beacon_id} -->
<!-- Generated: {datetime.now().isoformat()} -->
<audit_log>
    <metadata>
        <generated_by>SecureBank Audit System</generated_by>
        <period>2024-12</period>
        <total_events>{len(events)}</total_events>
    </metadata>
    <events>
{chr(10).join(events)}
    </events>
</audit_log>'''
    
    def _generate_config_xml(self, beacon_id):
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Config ID: {beacon_id} -->
<webhook_configuration>
    <endpoints>
        <endpoint name="payment_notifications">
            <url>https://api.internal.bank/webhooks/payments</url>
            <secret>whsec_{uuid.uuid4().hex[:24]}</secret>
            <events>payment.completed,payment.failed,payment.refunded</events>
        </endpoint>
        <endpoint name="account_updates">
            <url>https://api.internal.bank/webhooks/accounts</url>
            <secret>whsec_{uuid.uuid4().hex[:24]}</secret>
            <events>account.created,account.updated,account.closed</events>
        </endpoint>
        <endpoint name="fraud_alerts">
            <url>https://security.internal.bank/alerts</url>
            <secret>whsec_{uuid.uuid4().hex[:24]}</secret>
            <events>fraud.detected,fraud.confirmed</events>
        </endpoint>
    </endpoints>
    <authentication>
        <api_key>sk_live_{uuid.uuid4().hex}</api_key>
        <signing_secret>sig_{uuid.uuid4().hex[:32]}</signing_secret>
    </authentication>
</webhook_configuration>'''
    
    def _generate_transaction_xml(self, beacon_id):
        transactions = []
        for i in range(30):
            txn_id = f"TXN{random.randint(1000000000, 9999999999)}"
            amount = round(random.uniform(100, 500000), 2)
            from_acc = f"ACC{random.randint(100000000, 999999999)}"
            to_acc = f"ACC{random.randint(100000000, 999999999)}"
            timestamp = (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
            transactions.append(f'''    <transaction id="{txn_id}">
        <amount currency="USD">{amount}</amount>
        <from_account>{from_acc}</from_account>
        <to_account>{to_acc}</to_account>
        <timestamp>{timestamp}</timestamp>
        <type>{random.choice(["WIRE", "ACH", "INTERNAL", "SWIFT"])}</type>
        <status>COMPLETED</status>
    </transaction>''')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Export ID: {beacon_id} -->
<transaction_export>
    <period>2024-12</period>
    <total>{len(transactions)}</total>
    <transactions>
{chr(10).join(transactions)}
    </transactions>
</transaction_export>'''
    
    def _generate_generic_xml(self, beacon_id):
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<data id="{beacon_id}">
    <generated>{datetime.now().isoformat()}</generated>
    <content>Banking system export data</content>
</data>'''
    
    def generate_csv(self, filename, client_ip):
        """Generate CSV file with banking data"""
        beacon_id = str(uuid.uuid4())
        filepath = self.output_dir / f"{beacon_id}.csv"
        
        if "transaction" in filename.lower():
            content = self._generate_transaction_csv(beacon_id)
        elif "customer" in filename.lower() or "user" in filename.lower():
            content = self._generate_customer_csv(beacon_id)
        elif "account" in filename.lower():
            content = self._generate_account_csv(beacon_id)
        else:
            content = self._generate_summary_csv(beacon_id)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath, beacon_id
    
    def _generate_transaction_csv(self, beacon_id):
        rows = [f"# Export ID: {beacon_id}"]
        rows.append("transaction_id,date,from_account,to_account,amount,currency,type,status")
        for _ in range(100):
            txn_id = f"TXN{random.randint(1000000000, 9999999999)}"
            date = (datetime.now() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
            from_acc = f"ACC{random.randint(100000000, 999999999)}"
            to_acc = f"ACC{random.randint(100000000, 999999999)}"
            amount = round(random.uniform(100, 500000), 2)
            txn_type = random.choice(["WIRE", "ACH", "INTERNAL", "SWIFT", "PAYMENT"])
            rows.append(f"{txn_id},{date},{from_acc},{to_acc},{amount},USD,{txn_type},COMPLETED")
        return '\n'.join(rows)
    
    def _generate_customer_csv(self, beacon_id):
        rows = [f"# Export ID: {beacon_id}"]
        rows.append("customer_id,name,email,phone,account_number,balance,status")
        for _ in range(50):
            cust_id = f"CUS{random.randint(100000, 999999)}"
            name = fake.name()
            email = fake.email()
            phone = fake.phone_number()
            account = f"ACC{random.randint(100000000, 999999999)}"
            balance = round(random.uniform(1000, 5000000), 2)
            rows.append(f'{cust_id},"{name}",{email},{phone},{account},{balance},active')
        return '\n'.join(rows)
    
    def _generate_account_csv(self, beacon_id):
        rows = [f"# Export ID: {beacon_id}"]
        rows.append("account_id,holder_name,type,balance,currency,opened_date,status")
        for _ in range(30):
            acc_id = f"ACC{random.randint(100000000, 999999999)}"
            name = fake.company()
            acc_type = random.choice(["BUSINESS", "CORPORATE", "INVESTMENT", "SAVINGS"])
            balance = round(random.uniform(10000, 50000000), 2)
            opened = (datetime.now() - timedelta(days=random.randint(30, 1825))).strftime("%Y-%m-%d")
            rows.append(f'{acc_id},"{name}",{acc_type},{balance},USD,{opened},ACTIVE')
        return '\n'.join(rows)
    
    def _generate_summary_csv(self, beacon_id):
        rows = [f"# Export ID: {beacon_id}"]
        rows.append("date,deposits,withdrawals,transfers,net_change,balance")
        balance = 10000000
        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            deposits = round(random.uniform(50000, 500000), 2)
            withdrawals = round(random.uniform(30000, 300000), 2)
            transfers = round(random.uniform(10000, 100000), 2)
            net = deposits - withdrawals - transfers
            balance += net
            rows.append(f"{date},{deposits},{withdrawals},{transfers},{round(net, 2)},{round(balance, 2)}")
        return '\n'.join(rows)
    
    def generate_js(self, filename, client_ip):
        """Generate JavaScript config file"""
        beacon_id = str(uuid.uuid4())
        filepath = self.output_dir / f"{beacon_id}.js"
        
        if "terminal" in filename.lower():
            content = self._generate_terminal_config_js(beacon_id)
        else:
            content = self._generate_api_config_js(beacon_id)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath, beacon_id
    
    def _generate_terminal_config_js(self, beacon_id):
        return f'''// Terminal Configuration
// Config ID: {beacon_id}
// Generated: {datetime.now().isoformat()}

const terminalConfig = {{
    merchantId: "MCH{random.randint(1000000, 9999999)}",
    terminalId: "TRM{random.randint(100000, 999999)}",
    environment: "production",
    
    api: {{
        baseUrl: "https://gateway.internal.bank/v1",
        apiKey: "pk_live_{uuid.uuid4().hex}",
        secretKey: "sk_live_{uuid.uuid4().hex}",
        webhookSecret: "whsec_{uuid.uuid4().hex[:24]}"
    }},
    
    encryption: {{
        publicKey: "-----BEGIN PUBLIC KEY-----\\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA{uuid.uuid4().hex}\\n-----END PUBLIC KEY-----",
        keyId: "key_{uuid.uuid4().hex[:16]}"
    }},
    
    processing: {{
        currency: "USD",
        maxAmount: 100000,
        timeout: 30000,
        retryAttempts: 3
    }},
    
    security: {{
        pinEncryption: true,
        emvEnabled: true,
        p2peEnabled: true
    }}
}};

module.exports = terminalConfig;'''
    
    def _generate_api_config_js(self, beacon_id):
        return f'''// API Configuration
// Config ID: {beacon_id}
// Generated: {datetime.now().isoformat()}

module.exports = {{
    production: {{
        apiUrl: "https://api.internal.bank/v1",
        apiKey: "sk_live_{uuid.uuid4().hex}",
        webhookSecret: "whsec_{uuid.uuid4().hex[:24]}",
        encryptionKey: "{uuid.uuid4().hex}"
    }},
    
    database: {{
        host: "db-primary.internal.bank",
        port: 5432,
        name: "banking_prod",
        user: "api_service",
        password: "db_pass_{uuid.uuid4().hex[:16]}"
    }},
    
    redis: {{
        host: "redis.internal.bank",
        port: 6379,
        password: "redis_{uuid.uuid4().hex[:12]}"
    }},
    
    auth: {{
        jwtSecret: "{uuid.uuid4().hex}",
        tokenExpiry: 3600,
        refreshExpiry: 86400
    }}
}};'''
    
    def generate_json(self, filename, client_ip):
        """Generate JSON file"""
        beacon_id = str(uuid.uuid4())
        filepath = self.output_dir / f"{beacon_id}.json"
        
        if "credential" in filename.lower() or "key" in filename.lower():
            content = self._generate_credentials_json(beacon_id)
        elif "audit" in filename.lower():
            content = self._generate_audit_json(beacon_id)
        elif "config" in filename.lower():
            content = self._generate_config_json(beacon_id)
        else:
            content = self._generate_generic_json(beacon_id)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath, beacon_id
    
    def _generate_credentials_json(self, beacon_id):
        data = {
            "_document_id": beacon_id,
            "_generated": datetime.now().isoformat(),
            "api_credentials": {
                "live": {
                    "api_key": f"sk_live_{uuid.uuid4().hex}",
                    "secret_key": f"sec_{uuid.uuid4().hex}",
                    "webhook_secret": f"whsec_{uuid.uuid4().hex[:24]}"
                },
                "test": {
                    "api_key": f"sk_test_{uuid.uuid4().hex}",
                    "secret_key": f"sec_{uuid.uuid4().hex}",
                    "webhook_secret": f"whsec_{uuid.uuid4().hex[:24]}"
                }
            },
            "encryption_keys": {
                "primary": uuid.uuid4().hex,
                "secondary": uuid.uuid4().hex
            },
            "database": {
                "connection_string": f"postgresql://admin:db_pass_{uuid.uuid4().hex[:16]}@db-primary.internal.bank:5432/banking_prod"
            }
        }
        return json.dumps(data, indent=2)
    
    def _generate_audit_json(self, beacon_id):
        events = []
        for i in range(100):
            events.append({
                "id": i + 1,
                "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 720))).isoformat(),
                "type": random.choice(["LOGIN", "LOGOUT", "TRANSFER", "ACCESS", "MODIFY"]),
                "user_id": f"USR{random.randint(100000, 999999)}",
                "ip_address": f"192.168.{random.randint(1,254)}.{random.randint(1,254)}",
                "resource": f"/api/v1/accounts/ACC{random.randint(100000000, 999999999)}",
                "status": "SUCCESS"
            })
        data = {
            "_document_id": beacon_id,
            "_generated": datetime.now().isoformat(),
            "period": "2024-12",
            "total_events": len(events),
            "events": events
        }
        return json.dumps(data, indent=2)
    
    def _generate_config_json(self, beacon_id):
        data = {
            "_document_id": beacon_id,
            "payment_gateway": {
                "provider": "internal",
                "api_key": f"pk_{uuid.uuid4().hex}",
                "secret_key": f"sk_{uuid.uuid4().hex}",
                "webhook_url": "https://api.internal.bank/webhooks"
            },
            "processors": [
                {"name": "visa", "merchant_id": f"MID{random.randint(10000000, 99999999)}"},
                {"name": "mastercard", "merchant_id": f"MID{random.randint(10000000, 99999999)}"},
                {"name": "amex", "merchant_id": f"MID{random.randint(10000000, 99999999)}"}
            ]
        }
        return json.dumps(data, indent=2)
    
    def _generate_generic_json(self, beacon_id):
        data = {
            "_document_id": beacon_id,
            "_generated": datetime.now().isoformat(),
            "data": "Banking export data"
        }
        return json.dumps(data, indent=2)
