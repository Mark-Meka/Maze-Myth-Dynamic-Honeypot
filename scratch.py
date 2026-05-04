import re
import json

def sanitize_json(text):
    parts = text.split(r'\\')
    fixed_parts = []
    for part in parts:
        fixed_part = re.sub(r'\\(?![/\\bfnrtu"])', r'\\\\', part)
        fixed_parts.append(fixed_part)
    return r'\\'.join(fixed_parts)

tests = [
    r'{"a": "\l"}',
    r'{"a": "\\e"}',
    r'{"a": "\\\l"}',
    r'{"a": "\n"}',
    r'{"a": "\\n"}',
]

for t in tests:
    try:
        fixed = sanitize_json(t)
        res = json.loads(fixed, strict=False)
        print(f"PASS: {t} -> {fixed}")
    except Exception as e:
        print(f"FAIL: {t} -> {fixed} ({e})")
