import os
import json
import whisper
import subprocess
import requests

# --- DYNAMIC PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, "harvested_raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "shorts_ready")
META_DIR = os.path.join(BASE_DIR, "metadata")
TRANSCRIPT_DIR = os.path.join(BASE_DIR, "transcripts")

LLM_MODEL = "mistral"
MIN_LEN = 8
MAX_LEN = 60  # allowing more flexibility

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# --- TRANSCRIPTION ---
def transcribe_video(path):
    base_name = os.path.splitext(os.path.basename(path))[0]
    transcript_path = os.path.join(TRANSCRIPT_DIR, f"{base_name}.transcript.json")

    if os.path.exists(transcript_path):
        print(f"[📄] Cached transcript found for: {base_name}")
        with open(transcript_path, "r") as f:
            return json.load(f)["text"]

    print(f"\n[🎙️] TRANSCRIBING: {path}")
    model = whisper.load_model("base")
    result = model.transcribe(path)

    with open(transcript_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[✅] Transcription complete — {len(result['text'])} characters")
    return result['text']

# --- LLM-BASED SEGMENT DETECTION ---
def classify_segments_with_llm(transcript):
    print("[🧠] Querying Mistral LLM for viral-worthy segments...")

    system_prompt = """
You are a viral content expert. Your job is to extract SHORT, standalone, attention-grabbing moments 
from transcripts that would perform well on YouTube Shorts.

For each moment, return the following in a clean JSON array:
- start (in seconds)
- end (in seconds)
- title (hooky and viral)
- reason (why it was chosen)
- hashtags (relevant and trending, 3–6 max)
- comment_prompt (question to drive engagement)
- category (e.g., truth, comedy, motivation)

Keep segments between 8–60 seconds. Do not return explanation, only valid JSON.

Example:
[
  {
    "start": 75,
    "end": 93,
    "title": "This Will Blow Your Mind 🤯",
    "reason": "It reveals a shocking truth about human behavior.",
    "hashtags": ["#truthbomb", "#mindblown", "#fyp"],
    "comment_prompt": "Do you agree or disagree? 👇",
    "category": "truth"
  }
]
"""


    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": transcript.strip()}
        ],
        "stream": False
    }

    try:
        response = requests.post("http://localhost:11434/api/chat", json=payload)
        content = response.json()["message"]["content"].strip()

        if not content.startswith("["):
            content = content[content.find("["):]

        parsed = json.loads(content)
        print(f"[✅] LLM returned {len(parsed)} segment(s).")
        return parsed

    except Exception as e:
        print("[❌] LLM segment classification failed:", e)
        print("👀 LLM Raw Output Preview:\n", content[:300] if 'content' in locals() else "[No content returned]")
        return []

# --- CLIPPER ---
def slice_segment(video_path, out_path, start, end):
    if start >= end:
        print(f"[⚠️] Skipping invalid segment: start={start}, end={end}")
        return False

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(end - start),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "ultrafast",
        "-movflags", "+faststart",
        out_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"[❌] FFmpeg error for {out_path}:\n{result.stderr.decode()}")
        return False

    if os.path.getsize(out_path) < 10 * 1024:  # < 10 KB = junk
        print(f"[🗑️] Deleted junk slice: {out_path}")
        os.remove(out_path)
        return False

    print(f"[🎬] Clip saved: {out_path}")
    return True

# --- WORKFLOW ---
def run_slicer():
    print("\n[🚀] Running Smart Slicer...")
    files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".mp4")]

    if not files:
        print("[⚠️] No videos found in harvested_raw/")
        return

    for file in files:
        print(f"\n[📂] Processing: {file}")
        video_path = os.path.join(SOURCE_DIR, file)
        base_name = os.path.splitext(file)[0]

        transcript = transcribe_video(video_path)
        segments = classify_segments_with_llm(transcript)

        if not segments:
            print(f"[🚫] No usable segments for: {file}")
            continue

        for idx, seg in enumerate(segments):
            start, end = int(seg["start"]), int(seg["end"])
            title = seg["title"]
            clean_title = title.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("\"", "")[:40]
            out_file = f"{base_name}_{clean_title}_{idx+1:02d}.mp4"
            out_path = os.path.join(OUTPUT_DIR, out_file)
            meta_file = os.path.join(META_DIR, out_file.replace(".mp4", ".json"))

            success = slice_segment(video_path, out_path, start, end)
            if not success:
                if os.path.exists(meta_file):
                    os.remove(meta_file)
                continue

            meta = {
                "filename": out_file,
                "start": start,
                "end": end,
                "duration": round(end - start, 2),
                "title": title,
                "reason": seg.get("reason", ""),
                "source_video": file,
                "transcript_snippet": transcript[int(start):int(end)]
            }

            with open(meta_file, "w") as f:
                json.dump(meta, f, indent=2)
            print(f"[🧾] Metadata saved: {meta_file}")

    print("\n[✅] All done — clean smart clips + metadata ready!\n")

if __name__ == "__main__":
    run_slicer()
