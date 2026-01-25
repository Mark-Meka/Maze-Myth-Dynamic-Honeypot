"""
API Maze Generator - Creates interconnected, realistic API responses
This module enhances the honeypot with logical directory structures and breadcrumbs
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional

class APIMazeGenerator:
    """Generates interconnected API maze with breadcrumbs and logical structure"""
    
    def __init__(self, structure_file=None):
        # Inline API structure - no external file needed
        self.categories = {
            "companies": {"prefix": "/companies", "requires_auth": False},
            "accounts": {"prefix": "/api/v1/accounts", "requires_auth": True},
            "transactions": {"prefix": "/api/v1/transactions", "requires_auth": True},
            "payments": {"prefix": "/api/v1/payments", "requires_auth": True},
            "merchants": {"prefix": "/merchants", "requires_auth": False},
            "reports": {"prefix": "/api/v1/reports", "requires_auth": True},
            "admin": {"prefix": "/api/v2/admin", "requires_auth": "admin"},
            "internal": {"prefix": "/internal", "requires_auth": "internal"}
        }
        
        self.breadcrumb_templates = {
            "auth": "Authenticate at /api/v1/auth/login",
            "admin": "Admin access required",
            "related": "See also: {endpoints}"
        }
        
        self.fake_tokens = {
            "user": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.user",
            "admin": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.admin",
            "internal": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.internal"
        }
    
    def determine_access_level(self, path: str, auth_token: Optional[str] = None) -> str:
        """Determine what access level the request has"""
        
        # Check if path matches any category
        for category_name, category in self.categories.items():
            if path.startswith(category['prefix']):
                required_auth = category.get('requires_auth', False)
                
                if not required_auth:
                    return "public"
                
                if auth_token is None:
                    return "unauthorized"
                
                # Check token level
                if required_auth == "admin" and auth_token == self.fake_tokens['admin']:
                    return "admin"
                elif required_auth == "internal" and auth_token == self.fake_tokens['internal']:
                    return "internal"
                elif required_auth == True and auth_token == self.fake_tokens['user']:
                    return "authenticated"
                else:
                    return "forbidden"
        
        return "public"
    
    def is_valid_endpoint(self, path: str, user_agent: str = "") -> bool:
        """
        Validate if the endpoint follows logical API patterns
        
        PERMISSIVE MODE: Accept all reasonable banking/API paths
        Only reject clearly garbage paths
        """
        import re
        
        # Detect directory busting tools
        is_dirbusting = self._is_directory_buster(user_agent, path)
        
        # PERMISSIVE - Accept all API paths
        path_lower = path.lower()
        
        # Always accept if starts with api/
        if path_lower.startswith("api/"):
            return True
        
        # Accept banking/financial keywords anywhere in path
        banking_keywords = [
            'account', 'transaction', 'customer', 'payment', 'transfer',
            'balance', 'statement', 'card', 'loan', 'deposit', 'withdraw',
            'invoice', 'report', 'export', 'user', 'auth', 'login', 'token',
            'profile', 'setting', 'config', 'admin', 'internal', 'debug',
            'docs', 'health', 'status', 'data', 'file', 'download', 'secret',
            'companies', 'merchants', 'terminals', 'webhooks', 'credentials'
        ]
        
        for keyword in banking_keywords:
            if keyword in path_lower:
                return True
        
        # Accept internal/admin paths
        if path_lower.startswith("internal/") or path_lower.startswith("admin/"):
            return True
        
        # If directory buster, accept to tarpit them
        if is_dirbusting:
            return True
        
        # REJECT only garbage patterns
        garbage_patterns = [
            r"^\d+$",  # Just numbers
            r"\.(php|aspx?|jsp|cgi)$",  # Server scripts
        ]
        
        for pattern in garbage_patterns:
            if re.search(pattern, path_lower):
                return False
        
        # Default: ACCEPT (be permissive)
        return True

    
    def _is_directory_buster(self, user_agent: str, path: str) -> bool:
        """Detect if request is from a directory busting tool"""
        import re
        
        # Common directory busting tool signatures
        buster_signatures = [
            'dirb', 'dirbuster', 'gobuster', 'wfuzz', 'ffuf',
            'feroxbuster', 'dirsearch', 'nikto', 'burpsuite',
            'python-requests', 'go-http-client'
        ]
        
        ua_lower = user_agent.lower()
        for sig in buster_signatures:
            if sig in ua_lower:
                return True
        
        # Common wordlist paths that indicate directory busting
        common_wordlist_paths = [
            'admin.php', 'login.php', 'index.php', 'test.php',
            'admin.aspx', 'login.aspx', 'default.aspx',
            'wp-admin/', 'phpmyadmin/', 'administrator/',
            'backup/', 'temp/', 'tmp/', 'test/', 'old/',
            'config.php', 'db.php', 'database.php',
            '.git', '.env', '.htaccess', 'web.config'
        ]
        
        for wordlist_path in common_wordlist_paths:
            if wordlist_path in path.lower():
                return True
        
        return False

    
    def get_suggested_endpoints(self, current_path: str, access_level: str) -> List[str]:
        """Get endpoints to hint at based on current position"""
        suggestions = []
        
        # Suggest auth if unauthorized
        if access_level == "unauthorized":
            suggestions.append("/api/v1/auth/login")
        
        # Suggest elevation if forbidden
        elif access_level == "forbidden":
            suggestions.append("/api/v1/auth/elevate")
        
        # Suggest related endpoints based on current path
        elif "/users" in current_path:
            suggestions.extend([
                "/api/v1/users/123/profile",
                "/api/v2/admin/users" if access_level == "admin" else None
            ])
        elif "/products" in current_path:
            suggestions.extend([
                "/api/v1/orders",
                "/api/v1/products/456/inventory"
            ])
        elif "/admin" in current_path:
            suggestions.extend([
                "/internal/debug/trace",
                "/api/v2/admin/settings"
            ])
        elif "/internal" in current_path:
            suggestions.extend([
                "/internal/deploy/status",
                "/internal/config/secrets"
            ])
        
        # Filter out None values
        suggestions = [s for s in suggestions if s]
        
        return suggestions[:2]  # Limit to 2 suggestions
    
    def enhance_prompt_with_context(self, path: str, method: str, access_level: str) -> str:
        """Create enhanced prompt for Gemini with maze context"""
        
        suggested_endpoints = self.get_suggested_endpoints(path, access_level)
        
        base_prompt = f"""You are simulating a realistic corporate REST API endpoint.

Endpoint: {method} {path}
Access Level: {access_level}

Generate a realistic JSON response that:
1. Matches the endpoint's purpose (users, products, admin, debug, etc.)
2. Includes realistic field names and data types
3. """
        
        if access_level == "unauthorized":
            base_prompt += """Returns a 401 Unauthorized error with:
   - "error": "Unauthorized"
   - "message": "Authentication required"
   - "hint": "POST /api/v1/auth/login to obtain a token"
"""
        elif access_level == "forbidden":
            base_prompt += """Returns a 403 Forbidden error with:
   - "error": "Forbidden"
   - "message": "Insufficient permissions"
   - "hint": "Request elevation at /api/v1/auth/elevate"
"""
        else:
            base_prompt += f"""Includes subtle hints to other endpoints:
   - Add a "related_endpoints" or "_links" field mentioning: {suggested_endpoints}
   - Or include hints in comments/notes fields
   - Make it look natural, not forced"""
        
        base_prompt += "\n\nReturn ONLY valid JSON, no explanations."
        
        return base_prompt
    
    def add_breadcrumbs(self, response_data: Dict, path: str, access_level: str) -> Dict:
        """Add breadcrumb hints to the response"""
        
        suggested = self.get_suggested_endpoints(path, access_level)
        
        if suggested and access_level not in ["unauthorized", "forbidden"]:
            # Add hints naturally
            if random.random() > 0.5:
                response_data["_links"] = {
                    "related": suggested
                }
            else:
                template = random.choice(self.breadcrumb_templates)
                response_data["_meta"] = {
                    "hint": template.format(endpoint=suggested[0])
                }
        
        return response_data
    
    def generate_auth_response(self, endpoint: str) -> Dict:
        """Generate fake authentication responses"""
        
        if endpoint == "/api/v1/auth/login":
            return {
                "success": True,
                "token": self.fake_tokens['user'],
                "message": "Authentication successful",
                "hint": "Use this token in Authorization header for protected endpoints"
            }
        
        elif endpoint == "/api/v1/auth/elevate":
            return {
                "success": True,
                "admin_token": self.fake_tokens['admin'],
                "message": "Elevated to admin privileges",
                "warning": "Admin endpoints available at /api/v2/admin/*"
            }
        
        elif endpoint == "/api/v1/auth/internal":
            return {
                "success": True,
                "internal_token": self.fake_tokens['internal'],
                "message": "Internal access granted",
                "note": "Internal debugging endpoints: /internal/*"
            }
        
        return {}
