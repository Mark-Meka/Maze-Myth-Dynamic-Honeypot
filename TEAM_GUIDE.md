# 🚀 Quick Guide: Adding Features to the Honeypot

> **Simple 5-minute guide for team members**

---

## 📝 The 5-Step Process

Adding a new feature is super easy! Just follow these 5 steps:

### Step 1: Create a Folder
Create a new folder in `src/` for your feature:
```bash
src/your_feature_name/
```

### Step 2: Create Your Code File
Create a Python file with your feature code:
```python
# src/your_feature_name/feature.py

class YourFeature:
    def __init__(self):
        print("Your feature is ready!")
    
    def do_something(self, data):
        # Your code here
        return "Result"
```

### Step 3: Create `__init__.py`
Create this file to make it importable:
```python
# src/your_feature_name/__init__.py

from .feature import YourFeature
__all__ = ['YourFeature']
```

### Step 4: Use in `honeypot.py`
Add these 2 lines to `honeypot.py`:
```python
# At the top with imports
from src.your_feature_name import YourFeature

# In the initialization section
your_feature = YourFeature()

# Use it in a route
@app.route("/your-endpoint")
def your_endpoint():
    result = your_feature.do_something(request.data)
    return jsonify({"result": result})
```

### Step 5: Test It
Run the honeypot and test:
```bash
python honeypot.py

# In another terminal
curl http://localhost:8001/your-endpoint
```

**Done!** ✅

---

## 🎯 Complete Example: IP Blocker

Let's add a simple IP blocker feature together.

### 1. Create folder
```bash
mkdir src/ip_blocker
```

### 2. Create `src/ip_blocker/blocker.py`
```python
"""Simple IP blocker"""

class IPBlocker:
    def __init__(self):
        self.blocked_ips = set()
        print("[IP_BLOCKER] Ready!")
    
    def block_ip(self, ip):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        print(f"[IP_BLOCKER] Blocked {ip}")
    
    def is_blocked(self, ip):
        """Check if IP is blocked"""
        return ip in self.blocked_ips
    
    def unblock_ip(self, ip):
        """Unblock an IP address"""
        if ip in self.blocked_ips:
            self.blocked_ips.remove(ip)
            print(f"[IP_BLOCKER] Unblocked {ip}")
    
    def get_blocked_ips(self):
        """Get list of blocked IPs"""
        return list(self.blocked_ips)
```

### 3. Create `src/ip_blocker/__init__.py`
```python
from .blocker import IPBlocker
__all__ = ['IPBlocker']
```

### 4. Add to `honeypot.py`

**Import it:**
```python
from src.ip_blocker import IPBlocker
```

**Initialize it:**
```python
ip_blocker = IPBlocker()
```

**Use it in routes:**
```python
# Block IPs that make too many requests
@app.route("/<path:full_path>", methods=["GET", "POST", "PUT", "DELETE"])
def dynamic_endpoint(full_path):
    client_ip = request.remote_addr
    
    # Check if blocked
    if ip_blocker.is_blocked(client_ip):
        return jsonify({"error": "Access denied"}), 403
    
    # Your existing code...
    # ...

# Add management endpoints
@app.route("/admin/block/<ip>", methods=["POST"])
def block_ip(ip):
    ip_blocker.block_ip(ip)
    return jsonify({"message": f"Blocked {ip}"})

@app.route("/admin/unblock/<ip>", methods=["POST"])
def unblock_ip(ip):
    ip_blocker.unblock_ip(ip)
    return jsonify({"message": f"Unblocked {ip}"})

@app.route("/admin/blocked-ips")
def get_blocked_ips():
    return jsonify({"blocked_ips": ip_blocker.get_blocked_ips()})
```

### 5. Test it
```bash
# Start honeypot
python honeypot.py

# Block an IP
curl -X POST http://localhost:8001/admin/block/192.168.1.100

# Check blocked IPs
curl http://localhost:8001/admin/blocked-ips

# Unblock an IP
curl -X POST http://localhost:8001/admin/unblock/192.168.1.100
```

**That's it!** Your IP blocker is working! 🎉

---

## ✅ Checklist

When adding a feature, make sure you:

- [ ] Create folder in `src/`
- [ ] Create your Python file
- [ ] Create `__init__.py` file
- [ ] Import in `honeypot.py`
- [ ] Initialize your feature
- [ ] Add routes if needed
- [ ] Test it works

---

## 🎨 Template

Copy this template to start quickly:

**File: `src/my_feature/feature.py`**
```python
"""
My Feature - [What it does]
"""

class MyFeature:
    def __init__(self):
        """Initialize the feature"""
        print("[MY_FEATURE] Initialized!")
    
    def main_function(self, data):
        """Main functionality"""
        # Your code here
        result = f"Processed: {data}"
        return result
```

**File: `src/my_feature/__init__.py`**
```python
from .feature import MyFeature
__all__ = ['MyFeature']
```

**In `honeypot.py`:**
```python
# Import
from src.my_feature import MyFeature

# Initialize
my_feature = MyFeature()

# Use
@app.route("/my-route")
def my_route():
    result = my_feature.main_function(request.data)
    return jsonify({"result": result})
```

---

## 🆘 Common Issues

### Issue: "ModuleNotFoundError"
**Solution:** Make sure you created the `__init__.py` file

### Issue: Feature not working
**Solution:** Check you initialized it: `my_feature = MyFeature()`

### Issue: Can't access the route
**Solution:** Make sure honeypot is running and you used the correct URL

---

## 📚 Need More Help?

1. Look at existing features in `src/` folder for examples
2. Check `ADDING_FEATURES_GUIDE.md` for detailed examples
3. Ask the team!

---

## 🎯 Remember

The pattern is always the same:

```
1. Create folder     → src/feature_name/
2. Write code        → feature.py
3. Export it         → __init__.py
4. Import & use      → honeypot.py
5. Test              → curl or browser
```

**That's all you need to know!** 🚀

---

**Happy coding!** If you get stuck, the existing features in `src/` are great examples to learn from.
