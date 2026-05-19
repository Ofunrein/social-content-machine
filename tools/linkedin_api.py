import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.linkedin.com"
TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")


def _headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _author():
    return f"urn:li:person:{PERSON_URN}"


def create_text_post(text: str) -> dict:
    """Publish a text-only LinkedIn post."""
    payload = {
        "author": _author(),
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    resp = requests.post(
        f"{BASE_URL}/v2/ugcPosts",
        json=payload,
        headers={**_headers(), "Content-Type": "application/json"},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        return {"ok": True, "id": resp.json().get("id", "")}
    return {"ok": False, "error": resp.text}


def create_image_post(text: str, image_url: str) -> dict:
    """Publish a LinkedIn image post (3-step: register upload, PUT binary, create post)."""
    author = _author()

    # Step 1: Register upload
    reg_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    reg_resp = requests.post(
        f"{BASE_URL}/v2/assets?action=registerUpload",
        json=reg_payload,
        headers={**_headers(), "Content-Type": "application/json"},
        timeout=30,
    )
    if reg_resp.status_code not in (200, 201):
        return {"ok": False, "step": "register", "error": reg_resp.text}

    reg_data = reg_resp.json()["value"]
    upload_url = reg_data["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = reg_data["asset"]

    # Step 2: Upload binary
    img_bytes = requests.get(image_url, timeout=15).content
    put_resp = requests.put(
        upload_url,
        data=img_bytes,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/octet-stream"},
        timeout=30,
    )
    if put_resp.status_code not in (200, 201):
        return {"ok": False, "step": "upload", "error": put_resp.text}

    # Step 3: Create post with image
    post_payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [{"status": "READY", "media": asset_urn}],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    resp = requests.post(
        f"{BASE_URL}/v2/ugcPosts",
        json=post_payload,
        headers={**_headers(), "Content-Type": "application/json"},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        return {"ok": True, "id": resp.json().get("id", "")}
    return {"ok": False, "step": "post", "error": resp.text}
