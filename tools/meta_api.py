import os
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_URL = "https://graph.facebook.com/v21.0"
TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
IG_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")


def create_instagram_image_post(image_url: str, caption: str) -> dict:
    """Two-step Instagram publish: create container, then publish."""
    # Step 1: create container
    container_resp = requests.post(
        f"{GRAPH_URL}/{IG_ACCOUNT_ID}/media",
        params={"access_token": TOKEN, "image_url": image_url, "caption": caption},
        timeout=30,
    )
    container_data = container_resp.json()
    container_id = container_data.get("id")
    if not container_id:
        return {"ok": False, "step": "container", "error": container_resp.text}

    # Step 2: publish
    publish_resp = requests.post(
        f"{GRAPH_URL}/{IG_ACCOUNT_ID}/media_publish",
        params={"access_token": TOKEN, "creation_id": container_id},
        timeout=30,
    )
    publish_data = publish_resp.json()
    media_id = publish_data.get("id")
    if not media_id:
        return {"ok": False, "step": "publish", "error": publish_resp.text}

    return {"ok": True, "media_id": media_id}


def create_facebook_post(message: str) -> dict:
    """Post to Facebook Page feed."""
    resp = requests.post(
        f"{GRAPH_URL}/{PAGE_ID}/feed",
        json={"message": message, "access_token": PAGE_TOKEN},
        timeout=30,
    )
    data = resp.json()
    if "id" in data:
        return {"ok": True, "post_id": data["id"]}
    return {"ok": False, "error": resp.text}
