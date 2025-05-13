import os
import json
import whisper
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(__file__))

from segment_generator_hybrid import generate_segments

# --- SETUP ---
load_dotenv()
BASE = os.path.dirname(os.path.abspath(__file__))
DIRS = {
    "source": os.path.join(BASE, "harvested_raw"),
    "output": os.path.join(BASE, "shorts_ready"),
    "meta": os.path.join(BASE, "metadata"),
    "transcripts": os.path.join(BASE, "transcripts"),
}

for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# --- CONFIG ---
SUBTITLE_STYLE = {
    "font_path": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "font_size": 42,
    "font_color": (255, 255, 255),
    "stroke_color": (0, 0, 0),
    "stroke_width": 2,
    "bg_color": (0, 0, 0),
    "padding": 20,
    "align": ("center", "bottom"),
}

# --- UTILS ---
def transcribe(path):
    base = os.path.splitext(os.path.basename(path))[0]
    t_path = os.path.join(DIRS["transcripts"], f"{base}.json")
    if os.path.exists(t_path):
        print(f"[📄] Loaded cached transcript for: {base}")
        return json.load(open(t_path))["text"]

    print(f"[🎙️] Transcribing {base}...")
    model = whisper.load_model("base")
    result = model.transcribe(path)
    json.dump(result, open(t_path, "w"), indent=2)
    return result["text"]

def burn_subtitles(src, out, start, end, text):
    try:
        video = VideoFileClip(src)
        clip_duration = video.duration
        start = max(0, min(start, clip_duration - 0.5))
        end = max(start + 0.5, min(end, clip_duration))

        if start >= end:
            raise ValueError(f"Invalid start/end: start={start}, end={end}, video duration={clip_duration}")

        video = video.subclip(start, end)

        W, H = video.size
        font = ImageFont.truetype(SUBTITLE_STYLE["font_path"], SUBTITLE_STYLE["font_size"])
        lines = text.splitlines() or [text]

        img_height = SUBTITLE_STYLE["font_size"] * len(lines) + SUBTITLE_STYLE["padding"]
        img = Image.new("RGB", (W, img_height), color=SUBTITLE_STYLE["bg_color"])
        draw = ImageDraw.Draw(img)

        for i, line in enumerate(lines):
            w, h = draw.textbbox((0, 0), line, font=font)[2:]
            x = (W - w) / 2
            y = i * SUBTITLE_STYLE["font_size"]
            draw.text(
                (x, y),
                line,
                font=font,
                fill=SUBTITLE_STYLE["font_color"],
                stroke_width=SUBTITLE_STYLE["stroke_width"],
                stroke_fill=SUBTITLE_STYLE["stroke_color"]
            )

        img_path = os.path.join(DIRS["output"], "_subtitle_temp.png")
        img.save(img_path)

        txt_clip = ImageClip(img_path).set_duration(video.duration).set_position(SUBTITLE_STYLE["align"])
        final = CompositeVideoClip([video, txt_clip])
        final.write_videofile(out, codec='libx264', audio_codec='aac', preset='ultrafast', logger=None)
        return True

    except Exception as e:
        print(f"[❌] Subtitle burn failed: {e}")
        return False

# --- MAIN ---
def run_slicer():
    print("\n[🚀] Smart Slicer MVP\n")
    files = [f for f in os.listdir(DIRS["source"]) if f.endswith(".mp4")]
    print(f"[📁] Found {len(files)} file(s)")

    transcript_map = {}
    all_segments = []

    for f in files:
        path = os.path.join(DIRS["source"], f)
        base = os.path.splitext(f)[0]
        transcript = transcribe(path)
        transcript_map[base] = transcript

        print(f"[🧠] Generating segments for: {base}")
        try:
            segments = generate_segments(transcript)
            for seg in segments:
                seg["source_video"] = f"{base}.mp4"
            all_segments.extend(segments)
            print(f"[📦] Received {len(segments)} segment(s)\n")
        except Exception as e:
            print(f"[⚠️] Skipped {base}: {e}")

    for idx, seg in enumerate(all_segments):
        src_base = seg["source_video"].replace(".mp4", "")
        source_path = os.path.join(DIRS["source"], seg["source_video"])
        transcript_text = transcript_map.get(src_base, "")
        snippet = transcript_text[seg["start"]:seg["end"]]

        filename = f"{src_base}_{idx:02d}.mp4"
        out_path = os.path.join(DIRS["output"], filename)

        print(f"[🎬] Rendering: {filename}")
        if burn_subtitles(source_path, out_path, seg["start"], seg["end"], snippet):
            meta = {
                "filename": filename,
                "source_video": seg["source_video"],
                "start": seg["start"],
                "end": seg["end"],
                "title": seg["title"],
                "reason": seg["reason"],
                "transcript_snippet": snippet,
                "model_used": seg.get("model_used", "unknown")
            }
            meta_path = os.path.join(DIRS["meta"], filename.replace(".mp4", ".json"))
            json.dump(meta, open(meta_path, "w"), indent=2)
            print(f"[💾] Saved metadata: {meta_path}")

    print("\n[✅] Slicer MVP complete.")

if __name__ == "__main__":
    run_slicer()
