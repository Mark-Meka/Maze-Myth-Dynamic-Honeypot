"""
Utility script to create necessary assets for the API honeypot.
Run this once before starting the honeypot.
"""
from PIL import Image
from pathlib import Path
import os
def create_tracking_pixel():
    """Create a 1x1 transparent PNG for tracking"""
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # Create transparent 1x1 pixel
    img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    img.save(static_dir / "tracking_pixel.png")
    print("[OK] Created tracking pixel: static/tracking_pixel.png")
def create_directories():
    """Create necessary directories"""
    dirs = ["databases", "generated_files", "log_files", "static"]
    
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"[OK] Created directory: {dir_name}/")
def create_env_template():
    """Create .env template file"""
    env_content = """# API Honeypot Configuration
# OpenAI API Key (optional - system works without it using fallback responses)
# Get your key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_key_here
# Honeypot Server URL (change to your public IP/domain)
# This is used in tracking beacons
HONEYPOT_URL=http://localhost:8000
# Model to use (if using OpenAI)
LLM_MODEL=gpt-3.5-turbo
# Country code lookup (from existing honeypot)
COUNTRY=False
"""
    
    with open(".env.template", "w") as f:
        f.write(env_content)
    
    print("[OK] Created .env.template - copy to .env and configure")
def main():
    print("\n" + "="*60)
    print("[HONEYPOT] API Honeypot Setup Utility")
    print("="*60 + "\n")
    
    create_directories()
    create_tracking_pixel()
    create_env_template()
    
    print("\n" + "="*60)
    print("[OK] Setup complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. (Optional) Copy .env.template to .env and add your OpenAI API key")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run honeypot: python api_honeypot.py")
    print("\nSee QUICKSTART.md for detailed instructions.")
    print("="*60 + "\n")
if __name__ == "__main__":
    main()
