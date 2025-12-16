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
    
    def __init__(self, api_key="AIzaSyCbncHTb01bnPwND6eviaO4xoW8J43GJx4", model="gemini-2.0-flash"):
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
    
    def generate_api_response(self, path, method, context=None):
        """
        Generate realistic API response using Gemini
        
        Args:
            path: API endpoint path (e.g., /api/v1/users)
            method: HTTP method (GET, POST, etc.)
            context: Additional context for generation
            
        Returns:
            JSON string of generated response
        """
        prompt = f"""You are simulating a realistic corporate REST API endpoint.
Endpoint: {method} {path}
Context: {context or 'General corporate backend API'}
Generate a realistic JSON response that would be returned by this endpoint.
Include appropriate fields, realistic data values, and proper HTTP semantics.
Rules:
- Return ONLY valid JSON, no explanation, no markdown, no code blocks
- Use realistic field names and values
- Include metadata like timestamps, IDs, pagination if appropriate
- Make it look like a real production API
Example for GET /api/v1/users:
{{"users": [{{"id": 1, "username": "jdoe", "email": "jdoe@company.com", "role": "admin"}}], "total": 1}}
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
            # Fallback to template response
            return self._fallback_response(path, method)
    
    def _fallback_response(self, path, method):
        """Generate simple fallback response without LLM"""
        if method == "GET":
            return json.dumps({
                "data": [],
                "message": "Success",
                "timestamp": "2024-01-01T00:00:00Z"
            })
        elif method == "POST":
            return json.dumps({
                "id": 123,
                "status": "created",
                "message": "Resource created successfully"
            })
        else:
            return json.dumps({"message": "Success", "status": "ok"})
    
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