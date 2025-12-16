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
    
    def __init__(self, structure_file="api_structure_seed.json"):
        with open(structure_file, 'r') as f:
            self.structure = json.load(f)
        
        self.categories = self.structure['api_categories']
        self.breadcrumb_templates = self.structure['breadcrumb_templates']
        self.fake_tokens = self.structure['fake_tokens']
    
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
        
        STRICT MODE: Only accept real API resources (users, products, orders, etc.)
        TARPIT MODE: If directory buster detected, be slightly more permissive
        """
        import re
        
        # Detect directory busting tools
        is_dirbusting = self._is_directory_buster(user_agent, path)
        
        # STRICT validation - only logical API resources
        valid_patterns = [
            # Directory/discovery endpoints
            r"^api/v1/?$",  # /api/v1 or /api/v1/
            r"^api/v2/admin/?$",  # /api/v2/admin or /api/v2/admin/
            r"^internal/?$",  # /internal or /internal/
            
            # API v1 - only specific resources
            r"^api/v1/(users|products|orders|files|auth)(/|$)",
            r"^api/v1/users/(\d+|\{id\})(/profile|/settings|/orders)?$",
            r"^api/v1/products/(\d+|\{id\})(/inventory|/reviews)?$",
            r"^api/v1/orders/(\d+|\{id\})(/status|/items)?$",
            r"^api/v1/files/(\d+|\{id\})$",
            
            # API v2 admin - only specific resources
            r"^api/v2/admin/(users|analytics|settings|logs)(/|$)",
            r"^api/v2/admin/users/(\d+|\{id\})(/permissions)?$",
            
            # Internal - only specific resources
            r"^internal/(debug|config|deploy)(/|$)",
            r"^internal/debug/(trace|memory|logs)$",
            r"^internal/config/(database|secrets|env)$",
            r"^internal/deploy/(status|trigger)$",
        ]
        
        # Check strict patterns
        for pattern in valid_patterns:
            if re.match(pattern, path):
                return True
        
        # If directory buster, accept common scan patterns to tarpit them
        if is_dirbusting:
            tarpit_patterns = [
                r"(admin|login|test|backup|config)\.php$",
                r"(admin|login|test)\.aspx$",
                r"wp-admin|phpmyadmin",
                r"\.git|\.env|\.htaccess",
                r"^admin/|^administrator/|^backup/",
            ]
            
            for pattern in tarpit_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return True  # Tarpit these scanner patterns
        
        # Reject everything else
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
