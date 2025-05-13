import os
import json
import requests
from dotenv import load_dotenv
from collections import defaultdict
from difflib import SequenceMatcher

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Disabled for now

HEADERS_OPENAI = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {OPENAI_API_KEY}"
}

# HEADERS_GEMINI = {
#     "Content-Type": "application/json",
#     "x-goog-api-key": GEMINI_API_KEY
# }

PROMPT_GPT = """You are a Shorts virality expert. Return 3–5 viral segments in JSON with:
- start, end (sec), title (hook), reason, hashtags, comment_prompt, category, virality_score (1–10).
- Each must be 8–60s, standalone arc, emotional punch or insight. Strict JSON only."""

PROMPT_MISTRAL = """You're a viral detector for podcast content. Return 3–5 JSON segments with:
- start, end, title, reason, hashtags, comment_prompt, category, virality_score (1–10)
- Each must be 8–60s with hook, punchline, and standalone arc. Strictly return valid JSON array only."""

def test_llm_connections():
    print("\n[🔌] Testing LLM connectivity:")
    if OPENAI_API_KEY:
        try:
            r = requests.get("https://api.openai.com/v1/models", headers=HEADERS_OPENAI)
            print("[✅] GPT-4 connection: OK" if r.status_code == 200 else "[❌] GPT-4 connection: FAILED")
        except Exception as e:
            print(f"[❌] GPT-4 error: {e}")
    else:
        print("[⚠️] OPENAI_API_KEY not found")

    # if GEMINI_API_KEY:
    #     try:
    #         r = requests.post(
    #             "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-pro-exp-02-05:generateContent",
    #             headers=HEADERS_GEMINI,
    #             json={"contents": [{"parts": [{"text": "Say hello"}]}]}
    #         )
    #         print("[✅] Gemini connection: OK" if r.status_code == 200 else "[❌] Gemini connection: FAILED")
    #     except Exception as e:
    #         print(f"[❌] Gemini error: {e}")
    # else:
    #     print("[🟨] Gemini check skipped — currently disabled")

def similar(a, b, threshold=0.87):
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio() > threshold

def query_openai(transcript):
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": PROMPT_GPT},
            {"role": "user", "content": transcript.strip()}
        ]
    }
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=HEADERS_OPENAI, json=payload)
        content = r.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content[content.find("["):])
        for p in parsed:
            p["llm_votes"] = ["openai"]
        return parsed
    except Exception as e:
        print("[OpenAI ❌]", e)
        return []

def query_mistral_local(transcript, cache_key="mistral_segments.json"):
    base_dir = os.path.join(os.path.dirname(__file__), "transcripts")
    os.makedirs(base_dir, exist_ok=True)
    cache_path = os.path.join(base_dir, cache_key)

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)
                if isinstance(cached, list) and cached:
                    print(f"[📄] Loaded cached Mistral segments from {cache_key}")
                    return cached
                else:
                    os.remove(cache_path)
        except:
            os.remove(cache_path)

    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": PROMPT_MISTRAL},
            {"role": "user", "content": transcript.strip()}
        ],
        "stream": False
    }
    try:
        r = requests.post("http://localhost:11434/api/chat", json=payload)
        content = r.json()["message"]["content"].strip()
        trimmed = content[content.find("["):content.rfind("]")+1]
        parsed = json.loads(trimmed)
        for p in parsed:
            p["llm_votes"] = ["mistral"]
        with open(cache_path, "w") as f:
            json.dump(parsed, f, indent=2)
        return parsed
    except Exception as e:
        print("[Mistral ❌]", e)
        return []

def vote_segments(openai_segs, mistral_segs):  # Gemini commented out for now
    all_segments = openai_segs + mistral_segs
    consensus_map = []

    for new_seg in all_segments:
        match = None
        for existing in consensus_map:
            if (
                abs(existing["start"] - new_seg["start"]) < 2 and
                abs(existing["end"] - new_seg["end"]) < 2 and
                similar(existing["title"], new_seg["title"])
            ):
                existing["llm_votes"].extend(new_seg.get("llm_votes", []))
                match = existing
                break
        if not match:
            consensus_map.append(new_seg)

    voted = [s for s in consensus_map if len(set(s["llm_votes"])) >= 2]

    if not voted:
        print("[🧪] No agreement found — falling back to OpenAI top picks.")
        return sorted(openai_segs, key=lambda x: -x.get("virality_score", 5))[:5]

    return sorted(voted, key=lambda x: -x.get("virality_score", 5))

def get_consensus_segments(transcript, transcript_id="default"):
    meta_dir = os.path.join(os.path.dirname(__file__), "metadata")
    os.makedirs(meta_dir, exist_ok=True)
    cache_path = os.path.join(meta_dir, f"{transcript_id}.consensus.json")

    if os.path.exists(cache_path):
        print(f"[📄] Using cached consensus for: {transcript_id}")
        with open(cache_path, "r") as f:
            return json.load(f)

    mistral = query_mistral_local(transcript, f"{transcript_id}.mistral_segments.json")
    openai = query_openai(transcript)
    # gemini = []  # query_gemini(transcript)

    consensus = vote_segments(openai, mistral)

    with open(cache_path, "w") as f:
        json.dump(consensus, f, indent=2)
    return consensus
