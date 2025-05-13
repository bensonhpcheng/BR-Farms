# metadata_utils.py

import os
import json

def load_metadata_files(meta_dir):
    """Load all valid metadata JSON files into structured dicts."""
    metadata = []
    for file in os.listdir(meta_dir):
        if file.endswith(".json"):
            path = os.path.join(meta_dir, file)
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "reason" in data:
                        metadata.append(data)
            except Exception as e:
                print(f"[⚠️] Skipping invalid JSON: {file} ({e})")
    return metadata
