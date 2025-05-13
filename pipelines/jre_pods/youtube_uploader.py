import os
import json
import random
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client import file, client, tools

# --- CONFIG ---
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "shorts_ready")
META_DIR = os.path.join(os.path.dirname(__file__), "metadata")
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = "client_secrets.json"

HASHTAGS = [
    "#viral", "#shorts", "#dopamine", "#wtf", "#realtalk", "#uncensored",
    "#brainrot", "#truthbomb", "#fyp", "#triggered", "#mindblown"
]

# --- Authenticate YouTube API ---
def get_authenticated_service():
    store = file.Storage("oauth2.json")
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS_FILE, SCOPES)
        creds = tools.run_flow(flow, store)
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

# --- Generate dynamic comment based on metadata ---
def generate_engagement_comment(title, reason=""):
    prompts = [
        lambda t, r: f"What’s your take on this? 👇 #debate",
        lambda t, r: f"Do you agree or disagree with this? 🤔",
        lambda t, r: f"Would you say this out loud? 😳🗣️",
        lambda t, r: f"How true is this on a scale from 1–10? 🔥",
        lambda t, r: f"Someone had to say it... right? 💬",
        lambda t, r: f"{r.strip()} Agree or cap? 🧢" if r else f"Real talk or nah? 👀",
    ]
    return random.choice(prompts)(title.strip(), reason.strip())

# --- Upload the video ---
def upload_video(youtube, video_path, meta_path):
    with open(meta_path, "r") as f:
        meta = json.load(f)

    title = meta["title"]
    description = f"{meta.get('reason', '')}\n\nSubscribe for more 💀🔥\n{' '.join(random.sample(HASHTAGS, 5))}"
    tags = random.sample(HASHTAGS, 7)

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )
    response = request.execute()
    video_id = response["id"]
    print(f"[✅] Uploaded: {title} — https://youtu.be/{video_id}")

    # Leave a first comment
    comment = generate_engagement_comment(meta["title"], meta.get("reason", ""))
    youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": comment
                    }
                }
            }
        }
    ).execute()
    print(f"[💬] Comment posted: {comment}")

# --- Main uploader routine ---
def main():
    youtube = get_authenticated_service()

    videos = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".mp4")]
    if not videos:
        print("[⚠️] No videos found.")
        return

    random.shuffle(videos)
    for video_file in videos:
        video_path = os.path.join(UPLOAD_DIR, video_file)
        meta_file = os.path.join(META_DIR, video_file.replace(".mp4", ".json"))

        if not os.path.exists(meta_file):
            print(f"[!] Missing metadata for {video_file}. Skipping.")
            continue

        try:
            upload_video(youtube, video_path, meta_file)
        except Exception as e:
            print(f"[❌] Failed to upload {video_file}: {e}")
            continue

        wait = random.randint(300, 600)
        print(f"[⏱️] Waiting {wait//60} min before next upload...")
        time.sleep(wait)

if __name__ == "__main__":
    main()
