import whisper
import os
import random
import json
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import VideoFileClip

# --- CONFIG ---
SOURCE_DIR = "harvested_raw"
OUTPUT_DIR = "shorts_ready"
METADATA_DIR = "metadata"
MODEL = whisper.load_model("base")  # "small", "medium", etc.

MIN_LEN = 8
MAX_LEN = 30

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

# --- Utility: Transcribe video and return detailed word-timestamps ---
def transcribe_with_timestamps(video_path):
    print(f"[*] Transcribing {video_path}...")
    return MODEL.transcribe(video_path, word_timestamps=True)

# --- Utility: Identify "hot" segments using keywords and durations ---
def find_good_segments(transcript):
    hot_keywords = [
        "insane", "crazy", "truth", "money", "nobody", "illegal",
        "wtf", "he said", "she did", "they don't want you", "you won't believe"
    ]

    segments = transcript["segments"]
    good_chunks = []

    for seg in segments:
        text = seg["text"].lower()
        duration = seg["end"] - seg["start"]

        if MIN_LEN <= duration <= MAX_LEN and any(kw in text for kw in hot_keywords):
            metadata = {
                "start": seg["start"],
                "end": seg["end"],
                "duration": duration,
                "text": seg["text"],
                "classification": classify_text(seg["text"])
            }
            good_chunks.append(metadata)

    return good_chunks

# --- Utility: Quick content classifier based on keywords ---
def classify_text(text):
    lowered = text.lower()
    if "podcast" in lowered or "interview" in lowered:
        return "podcast"
    elif "meme" in lowered or "sound" in lowered:
        return "reaction"
    elif "money" in lowered or "redpill" in lowered:
        return "finance"
    elif "gym" in lowered or "lift" in lowered:
        return "fitness"
    else:
        return "general"

# --- Slice the clips and save + write metadata ---
def slice_and_save(video_path, base_name, chunks):
    for idx, clip in enumerate(chunks):
        out_name = f"{base_name}_smartclip{idx+1:02d}.mp4"
        out_path = os.path.join(OUTPUT_DIR, out_name)

        print(f"[+] Saving smart clip: {out_name} ({clip['duration']:.2f}s)")
        ffmpeg_extract_subclip(video_path, int(clip["start"]), int(clip["end"]), targetname=out_path)

        # Write accompanying metadata JSON
        meta = {
            "filename": out_name,
            "start": clip["start"],
            "end": clip["end"],
            "duration": clip["duration"],
            "text": clip["text"],
            "classification": clip["classification"],
            "resolution": get_resolution(video_path)
        }

        with open(os.path.join(METADATA_DIR, out_name.replace(".mp4", ".json")), "w") as f:
            json.dump(meta, f, indent=2)

# --- Get resolution of the source video ---
def get_resolution(path):
    clip = VideoFileClip(path)
    return f"{int(clip.w)}x{int(clip.h)}"

# --- Entry point ---
def run_smart_slicer():
    files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".mp4")]

    for file in files:
        path = os.path.join(SOURCE_DIR, file)
        base = os.path.splitext(file)[0]

        transcript = transcribe_with_timestamps(path)
        good_clips = find_good_segments(transcript)

        if not good_clips:
            print(f"[-] No good speech segments found in {file}.")
            continue

        slice_and_save(path, base, good_clips)

    print("\n[✓] Smart slicing complete.")

if __name__ == "__main__":
    run_smart_slicer()
