"""
HTTP Response Generator
Generates realistic HTTP status code responses for honeypot
"""
import random
import json
from datetime import datetime

class HTTPResponseGenerator:
    """Generate realistic HTTP responses with various status codes"""
    
    def __init__(self):
        self.error_codes = {
            '401': 'AUTH_001',
            '403': 'AUTH_003',
            '404': 'RES_404',
            '400': 'VAL_001',
            '500': 'SRV_500'
        }
    
    def generate_401_unauthorized(self, path):
        """Generate 401 Unauthorized response"""
        return {
            'status_code': 401,
            'response': {
                "error": "Unauthorized",
                "message": "Authentication credentials are missing or invalid",
                "code": self.error_codes['401'],
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "_hints": {
                    "authentication": "/api/v1/auth/login",
                    "documentation": "/api/docs"
                }
            },
            'headers': {
                'WWW-Authenticate': 'Bearer realm="api"',
                'Content-Type': 'application/json'
            }
        }
    
    def generate_403_forbidden(self, path, required_role='admin'):
        """Generate 403 Forbidden response"""
        return {
            'status_code': 403,
            'response': {
                "error": "Forbidden",
                "message": f"You do not have permission to access this resource",
                "code": self.error_codes['403'],
                "requiredRole": required_role,
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "_hints": {
                    "privilege_escalation": "/api/v1/auth/elevate",
                    "current_access": "user"
                }
            },
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    
    def generate_404_not_found(self, path):
        """Generate 404 Not Found response"""
        return {
            'status_code': 404,
            'response': {
                "error": "Not Found",
                "message": f"The requested resource at {path} was not found",
                "code": self.error_codes['404'],
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "_hints": {
                    "available_endpoints": [
                        "/api/v1",
                        "/api/v2",
                        "/api/docs"
                    ]
                }
            },
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    
    def generate_400_bad_request(self, path, validation_errors=None):
        """Generate 400 Bad Request response"""
        errors = validation_errors or [
            {"field": "amount", "message": "Invalid format"},
            {"field": "account_id", "message": "Required field missing"}
        ]
        
        return {
            'status_code': 400,
            'response': {
                "error": "Bad Request",
                "message": "Request validation failed",
                "code": self.error_codes['400'],
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            },
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    
    def generate_500_server_error(self, path):
        """Generate 500 Internal Server Error response"""
        import uuid
        return {
            'status_code': 500,
            'response': {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "code": self.error_codes['500'],
                "requestId": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "_hints": {
                    "support": "contact-support@securebank.com"
                }
            },
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    
    def should_return_error(self, path, has_auth=False, auth_level='none'):
        """
        Determine if this request should return an error
        
        Args:
            path: API endpoint path
            has_auth: Whether request has authentication
            auth_level: Level of auth (none, user, admin, internal)
        
        Returns:
            tuple: (should_error, status_code)
        """
        # Only highly sensitive paths require auth
        sensitive_paths = ['/admin/secrets', '/internal/', '/admin/config', '/api/internal']
        path_lower = path.lower()
        
        # Check if path is truly sensitive
        is_sensitive = any(sp in path_lower for sp in sensitive_paths)
        
        if is_sensitive:
            if not has_auth:
                return (True, 401)
            elif auth_level in ['none', 'public']:
                return (True, 403)
        
        # Very low chance of random errors (2% instead of 10%)
        if random.random() < 0.02:
            error_type = random.choices(
                [500, 400],
                weights=[0.7, 0.3]
            )[0]
            return (True, error_type)
        
        # Don't return 404 randomly - let the normal flow handle it
        return (False, 200)

    
    def get_response_for_status(self, status_code, path, **kwargs):
        """Get appropriate response for status code"""
        if status_code == 401:
            return self.generate_401_unauthorized(path)
        elif status_code == 403:
            return self.generate_403_forbidden(path, kwargs.get('required_role', 'admin'))
        elif status_code == 404:
            return self.generate_404_not_found(path)
        elif status_code == 400:
            return self.generate_400_bad_request(path, kwargs.get('validation_errors'))
        elif status_code == 500:
            return self.generate_500_server_error(path)
        else:
            return None  # Return 200 OK with normal response
