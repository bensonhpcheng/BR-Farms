import requests
import json
import os
from dotenv import load_dotenv
from pipelines.jre_pods.segment_generator_hybrid import run_mistral_prompt  # <-- you must define this client

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

GPT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {OPENAI_KEY}",
    "Content-Type": "application/json"
}

def generate_candidate_segments(transcript):
    prompt = f"""Analyze this full podcast transcript and extract up to 10 short-form video segments (10-90 seconds each) that are likely to go viral on YouTube Shorts. Return a JSON list of dicts with keys: start, end, title, reason.

Transcript:
{transcript}"""
    try:
        result = run_mistral_prompt(prompt)
        return json.loads(result) if isinstance(result, str) else result
    except Exception as e:
        print(f"[❌] Mistral error: {e}")
        return []

def score_with_gpt(segments):
    payload = {
        "model": "gpt-4",
        "messages": [{
            "role": "system",
            "content": "You are an expert at analyzing short-form video virality. Rate each proposed clip from 1 to 10 on how likely it is to go viral, and improve title + add 3 hashtags and a short comment prompt."
        }, {
            "role": "user",
            "content": f"Score and refine this list:\n{json.dumps(segments, indent=2)}"
        }],
        "temperature": 0.7
    }
    try:
        response = requests.post(GPT_ENDPOINT, headers=HEADERS, json=payload, timeout=30)
        result = response.json()
        if 'choices' not in result:
            print(f"[❌] GPT scoring failed: {result}")
            return []
        parsed = json.loads(result['choices'][0]['message']['content'])
        return parsed
    except Exception as e:
        print(f"[❌] GPT error: {e}")
        return []
