import os
import subprocess
import unicodedata
import string
import random
from datetime import datetime

# -- CONFIG --
KEYWORDS = [
    "gym motivation shorts",
    "conspiracy facts shorts",
    "viral tiktok moments",
    "basketball meme shorts",
    "redpill money advice",
    "sigma male grindset shorts",
    "stand up comedy shorts",
    "forbidden knowledge shorts",
    "brainrot meme shorts",
    "insane viral moments", 
    "oddly satisfying",
]
MAX_VIDEOS = 3  # per keyword
SAVE_DIR = "harvested_raw"
LOG_FILE = "harvest_log.txt"

os.makedirs(SAVE_DIR, exist_ok=True)

# -- Logging --
def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")

# -- Utility --
def sanitize_filename(name):
    valid_chars = f"{string.ascii_letters}{string.digits} -_.,()"
    return ''.join(c for c in unicodedata.normalize('NFKD', name) if c in valid_chars)

def randomize_keyword(keyword):
    prefixes = ["best", "top", "crazy", "insane", "wild", "ultimate", "viral"]
    suffixes = ["moments", "clips", "compilation", "fails", "highlights", "shorts"]
    return f"{random.choice(prefixes)} {keyword.split()[0]} {random.choice(suffixes)}"

# -- Harvest Routine --
def harvest_videos():
    initial_files = set(os.listdir(SAVE_DIR))

    for keyword in KEYWORDS:
        randomized_keyword = randomize_keyword(keyword)
        topic = randomized_keyword.replace(" ", "_").lower()
        search_term = f"ytsearch{MAX_VIDEOS}:{randomized_keyword}"

        log(f"[AIM] 🔍 Querying: {randomized_keyword}")

        try:
            subprocess.run([
                "yt-dlp",
                search_term,
"--format", "bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/best[height>=720]",
                "--match-filter",
                "duration >= 400 & duration <= 3600",
                "--restrict-filenames",
                "--format", "mp4",
                "--output",
                os.path.join(SAVE_DIR, f"{topic}_video%(autonumber)03d.%(ext)s")
            ], check=True)
        except Exception as e:
            log(f"[!] Error downloading '{randomized_keyword}': {e}")

    # Count the difference
    final_files = set(os.listdir(SAVE_DIR))
    harvested = final_files - initial_files
    log(f"\n[+] ✅ Harvest complete. {len(harvested)} new files saved to '{SAVE_DIR}'.")

# -- EXECUTE --
if __name__ == "__main__":
    harvest_videos()
