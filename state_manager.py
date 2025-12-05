"""
Dynamic API Honeypot - State Manager
This module handles persistence of generated endpoints and objects.
"""

from tinydb import TinyDB, Query
from pathlib import Path
from datetime import datetime

class APIStateManager:
    """Manages state persistence for the dynamic API honeypot"""
    
    def __init__(self, db_path="databases/api_state.json"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(db_path)
        self.endpoints = self.db.table('endpoints')
        self.objects = self.db.table('objects')
        self.beacons = self.db.table('beacons')
        
    def endpoint_exists(self, path, method):
        """Check if endpoint already generated"""
        Endpoint = Query()
        result = self.endpoints.search((Endpoint.path == path) & (Endpoint.method == method))
        return len(result) > 0
    
    def save_endpoint(self, path, method, response_template, description=""):
        """Save newly generated endpoint"""
        self.endpoints.insert({
            'path': path,
            'method': method,
            'response_template': response_template,
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
            'access_count': 1
        })
    
    def get_endpoint(self, path, method):
        """Retrieve saved endpoint and increment access count"""
        Endpoint = Query()
        result = self.endpoints.search((Endpoint.path == path) & (Endpoint.method == method))
        if result:
            # Increment access count
            self.endpoints.update({'access_count': result[0].get('access_count', 0) + 1}, 
                                doc_ids=[result[0].doc_id])
            return result[0]
        return None
    
    def save_object(self, object_type, object_id, data):
        """Save created object (e.g., user, product)"""
        self.objects.insert({
            'type': object_type,
            'id': str(object_id),
            'data': data,
            'created_at': datetime.utcnow().isoformat()
        })
    
    def get_objects_by_type(self, object_type):
        """Get all objects of a type (e.g., all users)"""
        Obj = Query()
        return self.objects.search(Obj.type == object_type)
    
    def get_object(self, object_type, object_id):
        """Get specific object"""
        Obj = Query()
        result = self.objects.search((Obj.type == object_type) & (Obj.id == str(object_id)))
        return result[0]['data'] if result else None
    
    def save_beacon(self, beacon_id, file_type, file_name, client_ip):
        """Save tracking beacon metadata"""
        self.beacons.insert({
            'beacon_id': beacon_id,
            'file_type': file_type,
            'file_name': file_name,
            'client_ip': client_ip,
            'generated_at': datetime.utcnow().isoformat(),
            'accessed_at': None,
            'access_count': 0
        })
    
    def activate_beacon(self, beacon_id, client_ip):
        """Mark beacon as accessed (file was opened)"""
        Beacon = Query()
        result = self.beacons.search(Beacon.beacon_id == beacon_id)
        if result:
            self.beacons.update({
                'accessed_at': datetime.utcnow().isoformat(),
                'access_count': result[0].get('access_count', 0) + 1,
                'activation_ip': client_ip
            }, doc_ids=[result[0].doc_id])
            return result[0]
        return None
    
    def get_all_endpoints(self):
        """Get all generated endpoints"""
        return self.endpoints.all()
    
    def get_statistics(self):
        """Get honeypot statistics"""
        return {
            'total_endpoints': len(self.endpoints),
            'total_objects': len(self.objects),
            'total_beacons': len(self.beacons),
            'activated_beacons': len([b for b in self.beacons if b.get('accessed_at')])
        }
