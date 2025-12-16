"""
Fine-tuning Script for Logical API Generation
Trains a model to generate realistic API endpoints from the honeypot dataset
"""

import json
import os
from pathlib import Path

# Configuration
DATASET_PATH = r"C:\Users\marco\Downloads\Maze-Myth-Dynamic-Honeypot\datasets\api_index.json"
OUTPUT_DIR = r"C:\Users\marco\.gemini\fine_tuning_output"
TRAINING_DATA_PATH = r"C:\Users\marco\.gemini\fine_tuning_data.jsonl"

def load_api_dataset(dataset_path):
    """Load the API index dataset"""
    print(f"Loading dataset from: {dataset_path}")
    
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[OK] Loaded {len(data)} API entries")
        return data
    except FileNotFoundError:
        print(f"[ERROR] Dataset not found at: {dataset_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        return None

def classify_api_endpoints(data):
    """
    Classify API endpoints by category, method, and access level
    Returns structured classification for fine-tuning
    """
    classifications = {
        "public": [],
        "authenticated": [],
        "admin": [],
        "internal": []
    }
    
    categories = {}
    
    # Data is a dict with API names as keys
    for api_name, api_info in data.items():
        # Extract version info
        preferred_version = api_info.get("preferred")
        if not preferred_version:
            continue
        
        versions = api_info.get("versions", {})
        if preferred_version not in versions:
            continue
        
        version_info = versions[preferred_version]
        info_block = version_info.get("info", {})
        
        # Get categories
        api_categories = info_block.get("x-apisguru-categories", ["general"])
        category = api_categories[0] if api_categories else "general"
        
        # Create simplified endpoint entry
        item = {
            "api_name": api_name,
            "endpoint": f"/api/{api_name}",
            "method": "GET",
            "category": category,
            "description": info_block.get("title", ""),
            "access_level": "public"  # Default for external APIs
        }
        
        # Classify by access level
        classifications["public"].append(item)
        
        # Classify by category
        if category not in categories:
            categories[category] = []
        categories[category].append(item)
    
    print("\n[STATS] Classification Results:")
    print(f"  Public endpoints: {len(classifications['public'])}")
    print(f"  Authenticated endpoints: {len(classifications['authenticated'])}")
    print(f"  Admin endpoints: {len(classifications['admin'])}")
    print(f"  Internal endpoints: {len(classifications['internal'])}")
    print(f"\n  Categories: {', '.join(list(categories.keys())[:10])}...")
    
    return classifications, categories

def create_training_examples(classifications):
    """
    Convert API dataset into training examples for fine-tuning
    Format: {"prompt": "...", "completion": "..."}
    """
    training_examples = []
    
    # Flatten all classifications into one list
    all_items = []
    for access_level, items in classifications.items():
        all_items.extend(items)
    
    for item in all_items:
        endpoint = item.get("endpoint", "")
        method = item.get("method", "GET")
        category = item.get("category", "general")
        description = item.get("description", "")
        
        # Create prompt-completion pairs
        prompt = f"Generate a {method} API endpoint for {category}"
        
        completion = {
            "endpoint": endpoint,
            "method": method,
            "description": description,
            "category": category
        }
        
        training_examples.append({
            "prompt": prompt,
            "completion": json.dumps(completion, ensure_ascii=False)
        })
    
    print(f"\n[OK] Created {len(training_examples)} training examples")
    return training_examples

def save_training_data(examples, output_path):
    """Save training examples in JSONL format for fine-tuning"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"\n[OK] Saved training data to: {output_path}")

def prepare_gemini_fine_tuning(examples):
    """
    Prepare data for Google Gemini fine-tuning
    Format: text-to-text examples
    """
    gemini_examples = []
    
    for example in examples:
        # Gemini format: {"text_input": "...", "output": "..."}
        gemini_examples.append({
            "text_input": example["prompt"],
            "output": example["completion"]
        })
    
    return gemini_examples

def generate_statistics(classifications, categories):
    """Generate comprehensive statistics about the dataset"""
    # Flatten all items from classifications
    all_items = []
    for access_level, items in classifications.items():
        all_items.extend(items)
    
    stats = {
        "total_endpoints": len(all_items),
        "access_levels": {k: len(v) for k, v in classifications.items()},
        "categories": {k: len(v) for k, v in categories.items()},
        "methods": {},
        "avg_endpoint_length": 0
    }
    
    # Count methods
    for item in all_items:
        method = item.get("method", "GET")
        stats["methods"][method] = stats["methods"].get(method, 0) + 1
    
    # Average endpoint length
    total_length = sum(len(item.get("endpoint", "")) for item in all_items)
    stats["avg_endpoint_length"] = total_length / len(all_items) if all_items else 0
    
    return stats

def main():
    """Main fine-tuning pipeline"""
    print("=" * 60)
    print("API FINE-TUNING PIPELINE")
    print("=" * 60)
    
    # Step 1: Load dataset
    data = load_api_dataset(DATASET_PATH)
    if not data:
        print("\n[ERROR] Failed to load dataset. Exiting.")
        return
    
    # Step 2: Classify endpoints
    classifications, categories = classify_api_endpoints(data)
    
    # Step 3: Generate statistics
    stats = generate_statistics(classifications, categories)
    print("\n[STATS] Dataset Statistics:")
    print(f"  Total endpoints: {stats['total_endpoints']}")
    print(f"  HTTP Methods: {stats['methods']}")
    print(f"  Avg endpoint length: {stats['avg_endpoint_length']:.1f} chars")
    
    # Step 4: Create training examples
    training_examples = create_training_examples(classifications)
    
    # Step 5: Save training data
    save_training_data(training_examples, TRAINING_DATA_PATH)
    
    # Step 6: Prepare for Gemini fine-tuning
    gemini_examples = prepare_gemini_fine_tuning(training_examples)
    gemini_path = os.path.join(OUTPUT_DIR, "gemini_training_data.jsonl")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(gemini_path, 'w', encoding='utf-8') as f:
        for example in gemini_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"[OK] Saved Gemini training data to: {gemini_path}")
    
    # Step 7: Save statistics
    stats_path = os.path.join(OUTPUT_DIR, "dataset_stats.json")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    
    print(f"[OK] Saved statistics to: {stats_path}")
    
    print("\n" + "=" * 60)
    print("[OK] FINE-TUNING PREPARATION COMPLETE!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Review training data: {TRAINING_DATA_PATH}")
    print(f"2. Upload to Google AI Studio for fine-tuning")
    print(f"3. Train model with Gemini API")
    print(f"\nOutput directory: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
