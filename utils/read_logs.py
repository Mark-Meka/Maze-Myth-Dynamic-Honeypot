"""
Read Encoded API Audit Logs
The honeypot encodes logs to prevent easy reading by attackers
"""
import sys
import base64

log_file = "log_files/api_audit.log"

# Check for command-line arguments
tail_lines = None
if len(sys.argv) > 1:
    if sys.argv[1] == "--tail" and len(sys.argv) > 2:
        tail_lines = int(sys.argv[2])

print("=" * 60)
print("API AUDIT LOG VIEWER (DECODED)")
print("=" * 60)
print()

try:
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Filter to tail if requested
    if tail_lines:
        lines = lines[-tail_lines:]
    
    # Decode each line
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        try:
            # Decode from Base64
            decoded = base64.b64decode(line).decode('utf-8')
            print(decoded)
        except Exception as e:
            # If not encoded, print as-is (for backward compatibility)
            print(line)
    
    print()
    print("=" * 60)
    print(f"Total lines: {len(lines)}")
    print("=" * 60)
    
except FileNotFoundError:
    print(f"ERROR: Log file not found: {log_file}")
    print("The honeypot may not have started yet.")
except Exception as e:
    print(f"ERROR: {e}")

print()
print("Usage:")
print("  python read_logs.py              # View all logs")
print("  python read_logs.py --tail 50    # View last 50 lines")
print("  python read_logs.py | findstr ATTACKER  # Search for attackers")
