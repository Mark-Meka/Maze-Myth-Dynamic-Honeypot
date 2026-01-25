"""SQLite Database Generator for Honeypot Bait Files"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

class SQLiteGenerator:
    """Generates realistic SQLite database files with contextual data"""
    
    def __init__(self, output_dir="generated_files/databases"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_database(self, context, beacon_id, endpoint_path="/api/data"):
        """Generate SQLite database with realistic tables and data"""
        
        # Determine database type from endpoint
        db_type = self._infer_db_type(endpoint_path)
        filename = f"{db_type}_{random.randint(1000, 9999)}.db"
        filepath = self.output_dir / filename
        
        # Create database
        conn = sqlite3.connect(str(filepath))
        cursor = conn.cursor()
        
        try:
            if db_type == "customers":
                self._create_customer_db(cursor, context)
            elif db_type == "transactions":
                self._create_transaction_db(cursor, context)
            elif db_type == "accounts":
                self._create_account_db(cursor, context)
            elif db_type == "logs":
                self._create_logs_db(cursor, context)
            else:
                self._create_generic_db(cursor, context)
            
            # Add beacon tracking table
            self._add_beacon_table(cursor, beacon_id)
            
            conn.commit()
        finally:
            conn.close()
        
        print(f"[SQLite] Generated {filename} ({filepath.stat().st_size} bytes)")
        return filepath, filename
    
    def _infer_db_type(self, endpoint):
        """Determine database type from endpoint path"""
        endpoint_lower = endpoint.lower()
        
        if 'customer' in endpoint_lower or 'user' in endpoint_lower:
            return 'customers'
        elif 'transaction' in endpoint_lower or 'payment' in endpoint_lower:
            return 'transactions'
        elif 'account' in endpoint_lower:
            return 'accounts'
        elif 'log' in endpoint_lower or 'audit' in endpoint_lower:
            return 'logs'
        else:
            return 'data'
    
    def _create_customer_db(self, cursor, context):
        """Create customer database"""
        cursor.execute('''
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                account_type TEXT,
                balance REAL,
                created_date TEXT,
                kyc_status TEXT
            )
        ''')
        
        # Insert realistic data
        for i in range(random.randint(50, 200)):
            cursor.execute('''
                INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                10000 + i,
                fake.name(),
                fake.email(),
                fake.phone_number(),
                random.choice(['premium', 'standard', 'basic', 'corporate']),
                round(random.uniform(100, 500000), 2),
                fake.date_between(start_date='-5y', end_date='today').isoformat(),
                random.choice(['verified', 'pending', 'incomplete'])
            ))
    
    def _create_transaction_db(self, cursor, context):
        """Create transaction database"""
        cursor.execute('''
            CREATE TABLE transactions (
                transaction_id TEXT PRIMARY KEY,
                from_account TEXT,
                to_account TEXT,
                amount REAL,
                currency TEXT,
                transaction_type TEXT,
                status TEXT,
                timestamp TEXT,
                description TEXT
            )
        ''')
        
        for i in range(random.randint(100, 500)):
            cursor.execute('''
                INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"TXN{random.randint(100000, 999999)}",
                f"ACC{random.randint(1000, 9999)}",
                f"ACC{random.randint(1000, 9999)}",
                round(random.uniform(10, 50000), 2),
                random.choice(['USD', 'EUR', 'GBP']),
                random.choice(['transfer', 'deposit', 'withdrawal', 'payment']),
                random.choice(['completed', 'pending', 'failed']),
                fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
                fake.sentence()
            ))
    
    def _create_account_db(self, cursor, context):
        """Create account database"""
        cursor.execute('''
            CREATE TABLE accounts (
                account_id TEXT PRIMARY KEY,
                customer_id INTEGER,
                account_type TEXT,
                balance REAL,
                currency TEXT,
                status TEXT,
                opened_date TEXT,
                last_transaction TEXT
            )
        ''')
        
        for i in range(random.randint(50, 150)):
            cursor.execute('''
                INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"ACC{10000 + i}",
                random.randint(1000, 9999),
                random.choice(['checking', 'savings', 'business', 'investment']),
                round(random.uniform(100, 1000000), 2),
                'USD',
                random.choice(['active', 'dormant', 'frozen']),
                fake.date_between(start_date='-10y', end_date='today').isoformat(),
                fake.date_time_between(start_date='-30d', end_date='now').isoformat()
            ))
    
    def _create_logs_db(self, cursor, context):
        """Create audit logs database"""
        cursor.execute('''
            CREATE TABLE audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_id TEXT,
                action TEXT,
                resource TEXT,
                ip_address TEXT,
                status TEXT,
                details TEXT
            )
        ''')
        
        actions = ['LOGIN', 'LOGOUT', 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 'DOWNLOAD', 'UPLOAD']
        resources = ['account', 'transaction', 'customer', 'report', 'settings']
        
        for i in range(random.randint(200, 1000)):
            cursor.execute('''
                INSERT INTO audit_logs (timestamp, user_id, action, resource, ip_address, status, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                fake.date_time_between(start_date='-90d', end_date='now').isoformat(),
                f"USR{random.randint(100, 999)}",
                random.choice(actions),
                random.choice(resources),
                fake.ipv4(),
                random.choice(['success', 'failed', 'blocked']),
                fake.sentence()
            ))
    
    def _create_generic_db(self, cursor, context):
        """Create generic data database"""
        cursor.execute('''
            CREATE TABLE data (
                id INTEGER PRIMARY KEY,
                key TEXT,
                value TEXT,
                category TEXT,
                created_at TEXT
            )
        ''')
        
        for i in range(random.randint(30, 100)):
            cursor.execute('''
                INSERT INTO data VALUES (?, ?, ?, ?, ?)
            ''', (
                i + 1,
                fake.word(),
                fake.text(max_nb_chars=100),
                random.choice(['config', 'settings', 'cache', 'metadata']),
                fake.date_time_this_year().isoformat()
            ))
    
    def _add_beacon_table(self, cursor, beacon_id):
        """Add hidden beacon tracking table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS _metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        cursor.execute('''
            INSERT INTO _metadata VALUES (?, ?)
        ''', ('tracking_id', beacon_id))
        
        cursor.execute('''
            INSERT INTO _metadata VALUES (?, ?)
        ''', ('generated_at', datetime.utcnow().isoformat()))
