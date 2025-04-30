import os
import random
import cv2
import subprocess
from moviepy.editor import VideoFileClip

# CONFIG
SOURCE_FOLDER = "harvested_raw"
OUTPUT_FOLDER = "shorts_ready"
CLIP_COUNT = 3
MIN_LEN = 10
MAX_LEN = 30
VERTICAL_RES = (1080, 1920)  # width x height

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_video_duration(path):
    clip = VideoFileClip(path)
    return clip.duration

def crop_to_vertical(frame):
    height, width = frame.shape[:2]
    target_width = int(height * 9 / 16)
    x_start = (width - target_width) // 2 if width > target_width else 0
    cropped = frame[:, x_start:x_start + target_width]
    return cv2.resize(cropped, VERTICAL_RES)

def slice_and_crop_video(file_path, base_name):
    duration = get_video_duration(file_path)
    if duration < MAX_LEN:
        print(f"[-] Skipping short video: {file_path}")
        return

    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    for i in range(CLIP_COUNT):
        start_time = random.randint(0, int(duration - MAX_LEN))
        clip_length = random.randint(MIN_LEN, MAX_LEN)
        out_name = os.path.join(OUTPUT_FOLDER, f"{base_name}_clip{i+1:03d}.mp4")

        print(f"[*] Slicing {file_path} at {start_time}s for {clip_length}s -> {out_name}")
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(out_name, fourcc, fps, VERTICAL_RES)

        frames_to_write = int(fps * clip_length)
        written = 0

        while cap.isOpened() and written < frames_to_write:
            ret, frame = cap.read()
            if not ret:
                break
            processed = crop_to_vertical(frame)
            out.write(processed)
            written += 1

        out.release()

    cap.release()

def run_slicer():
    video_files = [f for f in os.listdir(SOURCE_FOLDER) if f.endswith(('.mp4', '.mov'))]
    for video in video_files:
        full_path = os.path.join(SOURCE_FOLDER, video)
        base_name = os.path.splitext(video)[0]
        slice_and_crop_video(full_path, base_name)

    print("[+] All slicing complete. Check 'shorts_ready/' folder.")

if __name__ == '__main__':
    run_slicer()
