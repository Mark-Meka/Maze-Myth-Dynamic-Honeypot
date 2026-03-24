"""
RAG Document Loader for Honeypot Context
Loads and provides context from RAG directory for consistent API generation
"""

from pathlib import Path
import json

class RAGLoader:
    """Loads RAG documents to provide context for LLM-generated APIs"""
    
    def __init__(self, rag_dir="src/rag"):
        self.rag_dir = Path(rag_dir)
        self.context = {
            'api_patterns': [],
            'schemas': [],
            'sample_data': [],
            'company_info': {},
            'file_templates': []
        }
        self.load_documents()
    
    def load_documents(self):
        """Load all RAG documents"""
        if not self.rag_dir.exists():
            print(f"[RAG] Directory {self.rag_dir} not found, using defaults")
            self._load_defaults()
            return
        
        # Recursively find all relevant files
        for file_path in self.rag_dir.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                
                if ext in ['.md', '.txt']:
                    self._load_text_file(file_path)
                elif ext == '.json':
                    self._load_json_file(file_path)
        
        print(f"[RAG] Loaded context: {len(self.context['api_patterns'])} patterns, "
              f"{len(self.context['schemas'])} schemas, {len(self.context['sample_data'])} samples")
    
    def _load_text_file(self, file_path):
        """Load markdown or text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            filename = file_path.name.lower()
            
            # Categorize based on filename
            if 'schema' in filename or 'api' in filename:
                self.context['api_patterns'].append(content)
            elif 'data' in filename or 'sample' in filename:
                self.context['sample_data'].append(content)
            elif 'company' in filename or 'context' in filename:
                self.context['company_info']['description'] = content
            else:
                # General file templates
                self.context['file_templates'].append({
                    'name': file_path.stem,
                    'content': content
                })
        except Exception as e:
            print(f"[RAG] Error loading {file_path}: {e}")
    
    def _load_json_file(self, file_path):
        """Load JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle categorized_endpoints.json
            if file_path.name == 'categorized_endpoints.json':
                # Extract API patterns from endpoints
                if isinstance(data, list) and len(data) > 0:
                    self.context['api_patterns'].append(f"Loaded {len(data)} banking API endpoints")
                    # Use first few as schemas
                    for item in data[:5]:
                        if 'endpoint' in item:
                            self.context['schemas'].append(item['endpoint'])
            # Handle metadata.json
            elif file_path.name == 'metadata.json':
                self.context['company_info'].update(data)
            # Try to categorize JSON content
            elif isinstance(data, dict):
                if 'schema' in data or 'properties' in data:
                    self.context['schemas'].append(data)
                else:
                    self.context['sample_data'].append(data)
            elif isinstance(data, list):
                self.context['sample_data'].append(data)
        except Exception as e:
            print(f"[RAG] Error loading JSON {file_path}: {e}")
    
    def _load_defaults(self):
        """Load default banking/financial API context"""
        self.context = {
            'api_patterns': [
                "Banking API with endpoints for accounts, transactions, customers",
                "Financial services with payment processing and reporting",
                "Customer management with KYC and compliance data"
            ],
            'schemas': [
                {
                    'account': {
                        'account_id': 'string',
                        'customer_id': 'string',
                        'balance': 'decimal',
                        'account_type': 'string',
                        'status': 'string'
                    }
                },
                {
                    'transaction': {
                        'transaction_id': 'string',
                        'from_account': 'string',
                        'to_account': 'string',
                        'amount': 'decimal',
                        'timestamp': 'datetime',
                        'status': 'string'
                    }
                }
            ],
            'sample_data': [
                {'account_types': ['checking', 'savings', 'business', 'investment']},
                {'transaction_types': ['transfer', 'deposit', 'withdrawal', 'payment']}
            ],
            'company_info': {
                'description': 'SecureBank Financial Services - Enterprise Banking Platform',
                'domain': 'banking',
                'services': ['retail_banking', 'corporate_banking', 'investments']
            },
            'file_templates': []
        }
    
    def get_context_summary(self):
        """Get a summary of RAG context for LLM prompts"""
        summary = []
        
        if self.context['company_info']:
            company_desc = self.context['company_info'].get('description', 'Financial Services')
            if isinstance(company_desc, str):
                summary.append(f"Company: {company_desc}")
            else:
                summary.append("Company: SecureBank Financial Services")
        
        if self.context['api_patterns']:
            summary.append(f"API Patterns: {'; '.join(str(p) for p in self.context['api_patterns'][:3])}")
        
        if self.context['schemas']:
            schema_names = []
            for s in self.context['schemas'][:5]:
                if isinstance(s, dict):
                    if 'path' in s:
                        schema_names.append(s.get('path', 'unknown'))
                    else:
                        schema_names.append(list(s.keys())[0] if s.keys() else 'unknown')
            if schema_names:
                summary.append(f"Data Schemas: {', '.join(schema_names)}")
        
        return "\n".join(summary) if summary else "Banking/Financial Services API"
    
    def get_schema_for_endpoint(self, endpoint_path):
        """Get relevant schema based on endpoint path"""
        path_lower = endpoint_path.lower()
        
        # Try to find matching schema
        for schema in self.context['schemas']:
            if isinstance(schema, dict):
                schema_name = list(schema.keys())[0] if schema.keys() else ''
                if schema_name in path_lower or path_lower.endswith(schema_name):
                    return schema
        
        # Return first schema as fallback
        return self.context['schemas'][0] if self.context['schemas'] else {}
    
    def get_sample_data(self, data_type=None):
        """Get sample data for file generation"""
        if not self.context['sample_data']:
            return {}
        
        # If specific type requested, try to find it
        if data_type:
            for sample in self.context['sample_data']:
                if isinstance(sample, dict) and data_type in str(sample).lower():
                    return sample
        
        # Return random sample
        import random
        return random.choice(self.context['sample_data']) if self.context['sample_data'] else {}
    
    def get_company_name(self):
        """Get company name for file generation"""
        desc = self.context['company_info'].get('description', 'SecureBank Financial Services')
        if isinstance(desc, str):
            # Extract first part before dash or comma
            return desc.split('-')[0].split(',')[0].strip()
        return 'SecureBank Financial Services'
