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
        
        # DEFINED VALID ENDPOINTS - Only these paths return 200
        # Any path not matching these patterns returns 404
        self.valid_endpoints = [
            # Root level directories (gobuster will find these)
            "api", "admin", "internal", "companies", "merchants", "docs", "health",
            "login", "auth", "users", "config", "backup", "data", "export", "reports",
            "dashboard", "settings", "profile", "download", "upload", "files", "static",
            
            # API v1 endpoints
            "api/v1", "api/v1/accounts", "api/v1/transactions", "api/v1/payments",
            "api/v1/reports", "api/v1/auth", "api/v1/auth/login", "api/v1/auth/elevate",
            "api/v1/users", "api/v1/health", "api/v1/docs",
            
            # API v2 endpoints (admin)
            "api/v2", "api/v2/admin", "api/v2/admin/users", "api/v2/admin/settings",
            "api/v2/admin/logs", "api/v2/admin/secrets", "api/v2/admin/audit",
            
            # Internal endpoints (sensitive)
            "internal/config", "internal/debug", "internal/backups", "internal/logs",
            "internal/deploy", "internal/config/database", "internal/config/credentials",
            "internal/config/secrets",
            
            # Company endpoints
            "companies", "merchants",
            
            # File/download endpoints
            "api/download", "files", "export", "backup", "backups",
            
            # Common directories attackers look for
            "admin", "administrator", "login", "wp-admin", "phpmyadmin", 
            "console", "portal", "manage", "manager",
        ]
        
        # Patterns that match dynamic endpoints (ID-based)
        self.dynamic_patterns = [
            r"^api/v1/accounts/[A-Z0-9]+$",
            r"^api/v1/accounts/[A-Z0-9]+/transactions$",
            r"^api/v1/accounts/[A-Z0-9]+/statements$",
            r"^api/v1/transactions/[A-Z0-9]+$",
            r"^api/v1/payments/[A-Z0-9]+$",
            r"^companies/[A-Z0-9]+$",
            r"^companies/[A-Z0-9]+/accounts$",
            r"^companies/[A-Z0-9]+/apiCredentials$",
            r"^companies/[A-Z0-9]+/webhooks$",
            r"^merchants/[A-Z0-9]+$",
            r"^merchants/[A-Z0-9]+/terminals$",
            r"^api/v2/admin/users/[A-Z0-9]+$",
            r"^api/download/.+$",
        ]
        
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
        Check if path is a VALID endpoint that should return 200
        Returns False for paths that should return 404
        """
        import re
        
        path_lower = path.lower().strip('/')
        
        # Check exact match with valid endpoints
        if path_lower in [ep.lower() for ep in self.valid_endpoints]:
            return True
        
        # Check dynamic patterns (endpoints with IDs) - ONLY these patterns are valid
        for pattern in self.dynamic_patterns:
            if re.match(pattern, path, re.IGNORECASE):
                return True
        
        # Reject everything else with 404 - no prefix matching!
        return False

    
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
