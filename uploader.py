from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client import file, client, tools
import os
import random
import time
import cv2
import shutil
from PIL import Image, ImageDraw, ImageFont
import whisper

# -- CONFIG SETTINGS --
UPLOAD_FOLDER = 'source_vid'  # Folder containing videos
THUMBNAIL_FOLDER = 'thumbnails'  # Folder to store auto-generated thumbnails
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = "client_secrets.json"  # OAuth 2.0 credentials from Google Console

# -- HASHTAGS BANK --
HASHTAGS = [
    "#viral", "#shorts", "#brainrot", "#dopamine", "#mindblown", "#unexpected", "#truthbomb",
    "#hiddenknowledge", "#wtf", "#crazy", "#insane", "#fyp"
]

# -- ENGAGEMENT COMMENTS BANK --
COMMENTS = {
    "believe": "What would you do in this situation? 👇 #mindblown",
    "expected": "Did you see that coming? 😳💬 #unexpected",
    "blown": "Rate this moment 1-10 🔥🔥🔥 #viral",
    "stop": "Too real or too much? 😬👇 #truthbomb",
    "illegal": "Should this be allowed? Comment yes or no. ⛔✅",
    "secrets": "Which one shocked you the most? 👁️ #hiddenknowledge",
    "risk": "You made it this far… worth it? 🤔 #darkcontent"
}

os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

# Load Whisper model
model = whisper.load_model("small")

# -- Check if video is vertical (to qualify as a YouTube Short)
def is_vertical(filepath):
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        print(f"[!] Failed to open video: {filepath}")
        return False
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    cap.release()
    return height > width

def get_engagement_comment(title):
    for keyword, comment in COMMENTS.items():
        if keyword.lower() in title.lower():
            return comment
    return "What's your take? Sound off below! 👇 #shorts"

def generate_title_from_audio(filepath):
    print(f"[*] Generating title for {filepath}")
    result = model.transcribe(filepath, fp16=False)
    transcript = result['text'].strip()
    if len(transcript) > 60:
        transcript = transcript[:57] + "..."
    return transcript + " #shorts"

def generate_thumbnail(file_path, title):
    thumb_path = os.path.join(THUMBNAIL_FOLDER, os.path.splitext(os.path.basename(file_path))[0] + ".jpg")
    cap = cv2.VideoCapture(file_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
    success, frame = cap.read()
    if success:
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("arial.ttf", 40) if os.path.exists("arial.ttf") else ImageFont.load_default()
        draw.text((30, 30), title.split("#")[0], font=font, fill=(255, 255, 255))
        img.save(thumb_path)
        return thumb_path
    else:
        return None

def get_authenticated_service():
    store = file.Storage("oauth2.json")
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS_FILE, SCOPES)
        creds = tools.run_flow(flow, store)
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def upload_video(youtube, file_path):
    if not is_vertical(file_path):
        print(f"[-] Skipping {file_path} — Not vertical, won't qualify as a Short.")
        return

    title = generate_title_from_audio(file_path)
    comment = get_engagement_comment(title)
    selected_tags = random.sample(HASHTAGS, 5)

    description = f"Subscribe for more brainrot. 💀🔥\n\n{comment}\n\n{' '.join(selected_tags)}"
    category_id = "22"  # People & Blogs

    thumbnail_path = generate_thumbnail(file_path, title)

    body = dict(
        snippet=dict(
            title=title,
            description=description,
            tags=selected_tags,
            categoryId=category_id
        ),
        status=dict(
            privacyStatus="public"
        )
    )

    media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media_body
    )
    response = request.execute()
    print(f"[+] Uploaded {file_path} as '{title}'")

    if thumbnail_path:
        youtube.thumbnails().set(
            videoId=response['id'],
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        print(f"[+] Thumbnail uploaded: {thumbnail_path}")

def main():
    youtube = get_authenticated_service()
    video_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith((".mp4", ".mov"))]
    random.shuffle(video_files)

    for video_file in video_files:
        full_path = os.path.join(UPLOAD_FOLDER, video_file)
        upload_video(youtube, full_path)
        wait_time = random.randint(300, 900)  # Wait 5–15 minutes between uploads
        print(f"[+] Waiting {wait_time / 60:.2f} minutes before next upload...")
        time.sleep(wait_time)

if __name__ == '__main__':
    main()
