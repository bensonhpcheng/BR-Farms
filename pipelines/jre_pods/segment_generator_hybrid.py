import os
import json
import requests
import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = "http://localhost:11434/api/generate"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- SETUP ---
BASE = os.path.dirname(os.path.abspath(__file__))
FAIL_LOG_DIR = os.path.join(BASE, "fail_logs")
os.makedirs(FAIL_LOG_DIR, exist_ok=True)

SEGMENT_PROMPT_TEMPLATE = """
You are a viral content strategist analyzing the following podcast transcript. Identify 3 to 5 high-virality short-form video segments. For each one, give:
- A compelling title
- Start and end time (in seconds, estimate from transcript if not given)
- A one-sentence reason for virality
- Hashtags
- A target category
- A 1–2 sentence transcript snippet
- A viewer comment bait prompt

Format your response as a JSON array of objects with this format:

[
  {{
    "title": "...",
    "reason": "...",
    "start": 123,
    "end": 145,
    "snippet": "...",
    "hashtags": ["...", "..."],
    "category": "...",
    "comment_prompt": "..."
  }},
  ...
]

Transcript:
{transcript}
"""

# --- LOGGING ---
def log_failure(model: str, error: str, transcript: str, raw_output: str = None):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"fail_{model}_{timestamp}"
    log_path = os.path.join(FAIL_LOG_DIR, f"{base_name}.log")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"[MODEL]: {model}\n")
        f.write(f"[ERROR]: {error}\n\n")
        f.write("[TRANSCRIPT SNIPPET]\n")
        f.write(transcript[:1000])
    print(f"[🪵] Logged failure to: {log_path}")

    if raw_output:
        raw_path = os.path.join(FAIL_LOG_DIR, f"{base_name}_raw.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump({"model": model, "raw": raw_output}, f, indent=2)
        print(f"[🪵] Saved raw output to: {raw_path}")

# --- HELPERS ---
def query_ollama(prompt: str, model: str) -> str:
    res = requests.post(
        OLLAMA_URL,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=60
    )
    res.raise_for_status()
    return res.json()["response"]

def query_gpt_fallback(prompt: str) -> str:
    import openai
    from openai import OpenAI

    if not OPENAI_API_KEY:
        raise EnvironmentError("OPENAI_API_KEY not set in .env")

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a viral content strategist."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1024
    )
    return response.choices[0].message.content.strip()

def extract_json_block(text: str) -> List[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            start = text.index('[')
            end = text.rindex(']') + 1
            json_str = text[start:end]
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"JSON extraction failed: {e}\nRaw:\n{text[:1000]}")

# --- MAIN ENTRY ---
def generate_segments(transcript: str) -> List[Dict[str, Any]]:
    prompt = SEGMENT_PROMPT_TEMPLATE.format(transcript=transcript[:8000])
    segments = []
    model_used = "unknown"

    try:
        print("[🤖] Generating with Mistral...")
        raw = query_ollama(prompt, model="mistral")
        segments = extract_json_block(raw)
        model_used = "mistral"

    except Exception as mistral_error:
        log_failure("mistral", str(mistral_error), transcript)
        print(f"[Mistral ❌] {mistral_error}")

        try:
            print("[🦙] Falling back to LLaMA 3...")
            raw = query_ollama(prompt, model="llama3")
            segments = extract_json_block(raw)
            model_used = "llama3"
            log_failure("llama3", "[Used as fallback - no error]", transcript, raw_output=raw)

        except Exception as llama_error:
            log_failure("llama3", str(llama_error), transcript)
            print(f"[LLaMA ❌] {llama_error}")

            try:
                print("[💸] Final fallback to GPT-4...")
                raw = query_gpt_fallback(prompt)
                segments = extract_json_block(raw)
                model_used = "gpt-4"
                log_failure("gpt-4", "[Used as fallback - no error]", transcript, raw_output=raw)
            except Exception as gpt_error:
                log_failure("gpt-4", str(gpt_error), transcript)
                raise RuntimeError("[💀] All generation models failed. See fail_logs.")

    for seg in segments:
        seg.setdefault("title", "Untitled Segment")
        seg.setdefault("reason", "")
        seg.setdefault("start", 0)
        seg.setdefault("end", 15)
        seg.setdefault("snippet", "")
        seg.setdefault("hashtags", [])
        seg.setdefault("category", "general")
        seg.setdefault("comment_prompt", "What are your thoughts?")
        seg["source_video"] = "_combined"
        seg["model_used"] = model_used
        if model_used != "mistral":
            seg["title"] = f"[FAILED] {seg['title']}"

    return segments
