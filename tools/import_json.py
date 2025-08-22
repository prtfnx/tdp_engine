import sys
import os
import json
from PIL import Image

# Usage: python import_json.py <image_path> <frame_width> <frame_height> <output_json>

def main():
    if len(sys.argv) != 5:
        print("Usage: python import_json.py <image_path> <frame_width> <frame_height> <output_json>")
        sys.exit(1)

    image_path = sys.argv[1]
    frame_width = int(sys.argv[2])
    frame_height = int(sys.argv[3])
    output_json = sys.argv[4]

    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        sys.exit(2)

    img = Image.open(image_path)
    img_w, img_h = img.size
    frames_per_row = img_w // frame_width
    frames_per_col = img_h // frame_height
    total_frames = frames_per_row * frames_per_col

    frames = {}
    frame_idx = 0
    for row in range(frames_per_col):
        for col in range(frames_per_row):
            x = col * frame_width
            y = row * frame_height
            frames[f"frame_{frame_idx}"] = {
                "frame": {"x": x, "y": y, "w": frame_width, "h": frame_height},
                "rotated": False,
                "trimmed": False,
                "spriteSourceSize": {"x": 0, "y": 0, "w": frame_width, "h": frame_height},
                "sourceSize": {"w": frame_width, "h": frame_height},
                "pivot": {"x": 0.5, "y": 0.5}
            }
            frame_idx += 1

    atlas = {
        "frames": frames,
        "meta": {
            "version": "0.6.7",
            "image": os.path.basename(image_path),
            "format": "RGBA8888",
            "size": {"w": img_w, "h": img_h},
            "scale": 1
        }
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(atlas, f, indent=2)
    print(f"Saved atlas JSON to {output_json}")

if __name__ == "__main__":
    main()
