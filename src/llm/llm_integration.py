"""
LLM Integration Module
Handles API calls to Google Gemini for generating realistic responses.
"""
import google.generativeai as genai
import os
import json
import logging


class LLMGenerator:
    """Generate realistic API responses using Google Gemini"""
    
    def __init__(self, api_key="AIzaSyC0PVSenpHFc87mRxu7hogzewqpL8sTxuY", model="gemini-2.0-flash"):
        """
        Initialize Gemini generator
        
        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            model: Model to use (gemini-pro, gemini-1.5-pro, etc.)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise Exception("Google API key not found. Set GOOGLE_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)
        self.logger = logging.getLogger(__name__)
    
    def generate_api_response(self, path, method, context=None, rag_context=None):
        """
        Generate realistic API response using Gemini with RAG banking context
        
        Args:
            path: API endpoint path (e.g., /api/v1/accounts)
            method: HTTP method (GET, POST, etc.)
            context: Additional context for generation
            rag_context: RAG-loaded banking context for consistency
            
        Returns:
            JSON string of generated response
        """
        # Build banking-specific context
        banking_context = "Banking/Financial Services API"
        if rag_context:
            banking_context = rag_context.get_context_summary()
        
        prompt = f"""You are simulating a realistic BANKING REST API endpoint.
This is a Financial Services/Banking API system.

Endpoint: {method} {path}
System Context: {banking_context}
Additional Context: {context or 'Banking backend API'}

Generate a realistic JSON response that would be returned by this banking endpoint.

Banking Domain Guidelines:
- Use banking terminology: accounts, transactions, customers, balances, transfers
- Include account numbers (format: ACC followed by 8 digits)
- Include transaction IDs (format: TXN followed by 9 digits)
- Use realistic currency amounts in USD
- Include timestamps for transactions
- Add status fields (active, pending, completed, etc.)
- Include customer IDs and account types (checking, savings, business)

Rules:
- Return ONLY valid JSON, no explanation, no markdown, no code blocks
- Use realistic banking field names and values
- Include metadata like timestamps, IDs, pagination if appropriate
- Make it look like a real production banking API

Example for GET /api/v1/accounts:
{{"accounts": [{{"account_id": "ACC10025678", "customer_id": "CUS00123", "account_type": "checking", "balance": 5432.50, "currency": "USD", "status": "active"}}], "total": 1}}

Now generate for {method} {path}:"""
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                # Remove first and last lines (``` markers)
                content = "\n".join(lines[1:-1])
                if content.startswith("json"):
                    content = content[4:].strip()
            
            # Validate JSON
            json.loads(content)
            return content
            
        except Exception as e:
            self.logger.error(f"Gemini generation failed: {e}")
            # Fallback to banking template response
            return self._fallback_banking_response(path, method)
    
    def _fallback_banking_response(self, path, method):
        """Generate banking-specific fallback response without LLM"""
        import random
        from datetime import datetime, timedelta
        
        if method == "GET":
            # Determine response type from path
            if "account" in path.lower():
                return json.dumps({
                    "accounts": [
                        {
                            "account_id": f"ACC{random.randint(10000000, 99999999)}",
                            "customer_id": f"CUS{random.randint(100, 9999):05d}",
                            "account_type": random.choice(["checking", "savings", "business"]),
                            "balance": round(random.uniform(100, 50000), 2),
                            "currency": "USD",
                            "status": "active",
                            "opened_date": (datetime.now() - timedelta(days=random.randint(30, 1000))).isoformat()
                        }
                    ],
                    "total": 1
                })
            elif "transaction" in path.lower():
                return json.dumps({
                    "transactions": [
                        {
                            "transaction_id": f"TXN{random.randint(100000000, 999999999)}",
                            "from_account": f"ACC{random.randint(10000000, 99999999)}",
                            "to_account": f"ACC{random.randint(10000000, 99999999)}",
                            "amount": round(random.uniform(10, 5000), 2),
                            "currency": "USD",
                            "status": random.choice(["completed", "pending"]),
                            "timestamp": datetime.now().isoformat()
                        }
                    ],
                    "total": 1
                })
            elif "customer" in path.lower() or "user" in path.lower():
                return json.dumps({
                    "customers": [
                        {
                            "customer_id": f"CUS{random.randint(100, 9999):05d}",
                            "full_name": "John Doe",
                            "email": "john.doe@email.com",
                            "account_count": random.randint(1, 3),
                            "status": "verified"
                        }
                    ],
                    "total": 1
                })
            else:
                return json.dumps({
                    "data": [],
                    "message": "Success",
                    "timestamp": datetime.now().isoformat()
                })
        elif method == "POST":
            return json.dumps({
                "id": f"TXN{random.randint(100000000, 999999999)}",
                "status": "created",
                "message": "Transaction initiated successfully"
            })
        else:
            return json.dumps({"message": "Success", "status": "ok"})
    
    def _fallback_response(self, path, method):
        """Legacy fallback - redirect to banking fallback"""
        return self._fallback_banking_response(path, method)

    
    def generate_endpoint_description(self, path, method):
        """
        Generate Swagger/OpenAPI description for endpoint
        
        Returns:
            JSON string with endpoint documentation
        """
        prompt = f"""Generate a professional API endpoint description for Swagger/OpenAPI documentation.
Endpoint: {method} {path}
Provide a JSON object with these fields:
- summary: Brief one-line description
- description: Detailed explanation (2-3 sentences)
- tags: Array of relevant tags
- parameters: Array of parameter objects (if applicable)
- responses: Object with response codes and descriptions
Make it sound like enterprise software documentation.
Return ONLY valid JSON, no markdown, no code blocks."""
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text.strip()
            
            # Remove markdown if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
                if content.startswith("json"):
                    content = content[4:].strip()
            
            json.loads(content)  # Validate
            return content
            
        except Exception as e:
            self.logger.error(f"Description generation failed: {e}")
            return json.dumps({
                "summary": f"{method} {path}",
                "description": "API endpoint",
                "responses": {
                    "200": {"description": "Successful response"}
                }
            })
    
    def generate_file_content(self, file_type):
        """
        Generate realistic content for bait files
        
        Args:
            file_type: Type of file (pdf, excel, env)
            
        Returns:
            Dictionary with content data
        """
        prompts = {
            "pdf": "Generate realistic content for a corporate Q4 financial report. Include: revenue figures, expenses, profit, key metrics. Return as JSON with fields.",
            "excel": "Generate realistic employee directory data. Include: 10 employees with name, email, department, salary, hire_date. Return as JSON array.",
            "env": "Generate realistic production environment variables for a web application. Include: database URLs, API keys, AWS credentials, Redis URLs. Return as JSON object."
        }
        
        prompt = prompts.get(file_type, "Generate realistic corporate data as JSON.")
        prompt += "\n\nReturn ONLY valid JSON, no markdown, no code blocks."
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text.strip()
            
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
                if content.startswith("json"):
                    content = content[4:].strip()
            
            return json.loads(content)
            
        except Exception as e:
            self.logger.error(f"File content generation failed: {e}")
            return {"error": "Could not generate content"}