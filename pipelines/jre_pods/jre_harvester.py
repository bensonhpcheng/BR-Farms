import os
import subprocess
import datetime
import string
import unicodedata
from pathlib import Path

# --- CONFIG ---
BASE_DIR = Path(__file__).resolve().parent
KEYWORD_FILE = BASE_DIR / "jre_keywords.txt"
SAVE_DIR = BASE_DIR / "harvested_raw"
MAX_VIDEOS_PER_KEYWORD = 5
MIN_DURATION = 300    # 5 minutes
MAX_DURATION = 3600   # 60 minutes

os.makedirs(SAVE_DIR, exist_ok=True)

def sanitize_filename(name):
    valid_chars = f"{string.ascii_letters}{string.digits} -_.,()"
    return ''.join(c for c in unicodedata.normalize('NFKD', name) if c in valid_chars)

def read_keywords():
    with open(KEYWORD_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def harvest_video(keyword):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_keyword = sanitize_filename(keyword.replace(" ", "_").lower())
    print(f"[{timestamp[-6:]}] 🔍 Harvesting: {keyword}")

    search_term = f"ytsearch{MAX_VIDEOS_PER_KEYWORD}:{keyword}"
    try:
        subprocess.run([
            "yt-dlp",
            search_term,
            "--match-filter",
            f"duration >= {MIN_DURATION} & duration <= {MAX_DURATION}",
            "--restrict-filenames",
            "--format", "mp4",
            "--output", str(SAVE_DIR / f"{timestamp}_{clean_keyword}_video_%(id)s.%(ext)s")
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Error harvesting '{keyword}': {e}")

def main():
    keywords = read_keywords()
    for kw in keywords:
        harvest_video(kw)

    print(f"\n[✅] Harvest complete. Files saved to: {SAVE_DIR}")

if __name__ == "__main__":
    main()
