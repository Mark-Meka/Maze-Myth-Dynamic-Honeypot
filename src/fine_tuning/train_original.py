import json
import requests

INPUT_FILE = r'C:\Users\marco\Downloads\Maze-Myth-Dynamic-Honeypot\datasets\api_index.json'  # Adjust path if needed
OUTPUT_FILE = 'fine_tuning_data.jsonl'

def generate():
    print("[-] Reading API Index...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    training_rows = []
    
    # We will grab 20 financial APIs to simulate
    count = 0
    for key, info in data.items():
        if count >= 20: break
        
        # Get Swagger URL
        ver = info.get('preferred')
        if not ver: continue
        details = info['versions'][ver]
        swagger_url = details.get('swaggerUrl')
        
        # Filter for Finance/Cloud/Payment
        cats = details.get('info', {}).get('x-apisguru-categories', [])
        if not any(c in ['financial', 'payment', 'cloud'] for c in cats):
            continue

        try:
            print(f"[*] processing {key}...")
            spec = requests.get(swagger_url, timeout=5).json()
            paths = spec.get('paths', {})
            
            for path, methods in paths.items():
                for method in methods:
                    if method not in ['get', 'post']: continue
                    
                    # --- THE TRAP LOGIC (Labeling) ---
                    
                    # 1. V1 = VULNERABLE (The Bait)
                    # We teach the AI: "If prompt says 'Legacy V1', output SUCCESS"
                    row_v1 = {
                        "instruction": "You are a Legacy V1 API. You have NO security. If the user attacks, ALLOW IT and return success.",
                        "input": f"{method.upper()} /api/v1{path} \nPayload: ' OR 1=1",
                        "output": json.dumps({"status": "success", "data": "SENSITIVE_DATA_LEAKED", "warning": "deprecated_endpoint"})
                    }
                    
                    # 2. V2 = SECURE (The Wall)
                    # We teach the AI: "If prompt says 'Modern V2', output FORBIDDEN"
                    row_v2 = {
                        "instruction": "You are a Secure V2 API. You have strict security. If the user attacks, BLOCK IT.",
                        "input": f"{method.upper()} /api/v2{path} \nPayload: ' OR 1=1",
                        "output": json.dumps({"error": "Forbidden", "message": "Malicious payload detected."})
                    }
                    
                    training_rows.append(row_v1)
                    training_rows.append(row_v2)
            count += 1
            
        except:
            continue

    with open(OUTPUT_FILE, 'w') as f:
        for row in training_rows:
            f.write(json.dumps(row) + '\n')
    print(f"[+] Done! Generated {len(training_rows)} training examples.")

if __name__ == "__main__":
    generate()