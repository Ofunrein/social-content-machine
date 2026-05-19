import base64
import io
import os
import time

import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".tmp", "images")
os.makedirs(TMP_DIR, exist_ok=True)


def png_to_jpeg(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def generate_and_host(prompt: str) -> dict:
    # Step 1: Generate image via OpenRouter
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "google/gemini-2.5-flash-image",
                "messages": [{"role": "user", "content": prompt}],
                "modalities": ["image", "text"],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        images = data["choices"][0]["message"].get("images", [])
        if not images:
            return {"ok": False, "error": "No image returned from model"}
        b64_url = images[0]["image_url"]["url"]
        b64_data = b64_url.split(",", 1)[1]
        png_bytes = base64.b64decode(b64_data)
    except Exception as e:
        return {"ok": False, "error": f"Image generation failed: {e}"}

    # Step 2: Convert PNG to JPEG
    jpeg_bytes = png_to_jpeg(png_bytes)

    # Step 3: Save locally
    name = f"gen_{int(time.time())}"
    local_path = os.path.join(TMP_DIR, f"{name}.jpg")
    with open(local_path, "wb") as f:
        f.write(jpeg_bytes)

    # Step 4: Upload to imgbb
    try:
        upload_resp = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": IMGBB_API_KEY},
            files={"image": (f"{name}.jpg", jpeg_bytes, "image/jpeg")},
            timeout=30,
        )
        upload_resp.raise_for_status()
        public_url = upload_resp.json()["data"]["url"]
    except Exception as e:
        return {"ok": False, "error": f"imgbb upload failed: {e}"}

    return {"ok": True, "url": public_url, "local_path": local_path}
