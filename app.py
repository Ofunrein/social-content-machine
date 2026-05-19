import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))

import openai
from flask import Flask, jsonify, render_template, request, send_from_directory
from dotenv import load_dotenv

from linkedin_api import create_text_post, create_image_post
from meta_api import create_instagram_image_post, create_facebook_post
from generate_image import generate_and_host
from generate_content import generate_post
from scrape_competitors import scrape_instagram, scrape_linkedin

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
app = Flask(__name__)
TMP_DIR = os.path.join(os.path.dirname(__file__), ".tmp")
os.makedirs(os.path.join(TMP_DIR, "competitors"), exist_ok=True)
os.makedirs(os.path.join(TMP_DIR, "images"), exist_ok=True)


@app.route("/")
def research_page():
    return render_template("research.html")


@app.route("/create")
def create_page():
    return render_template("create.html")


@app.route("/api/analyze-competitor", methods=["POST"])
def api_analyze_competitor():
    data = request.get_json()
    platform = (data.get("platform") or "instagram").strip()
    handle = (data.get("handle") or "").strip().lstrip("@")

    if not handle:
        return jsonify({"error": "Handle is required"}), 400

    if platform == "instagram":
        posts = scrape_instagram([handle])
    else:
        posts = scrape_linkedin([handle])

    if not posts:
        return jsonify({"error": "No posts found. Check the handle."}), 404

    # Save raw posts
    cache_path = os.path.join(TMP_DIR, "competitors", f"{platform}_{handle}_{int(time.time())}.json")
    with open(cache_path, "w") as f:
        json.dump(posts, f, indent=2)

    # AI analysis via Gemini Flash
    client = openai.OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    prompt = f"""Analyze these {platform} posts from @{handle} and provide:
1. "outliers" - top 3-5 posts that performed significantly above average (include the post text/caption snippet, why it worked, engagement stats)
2. "content_ideas" - 5 content suggestions inspired by their strategy, each with: title, angle, recommended_format, hashtags (list), rationale

Return ONLY valid JSON with keys "outliers" and "content_ideas". No markdown fences.

Posts data:
{json.dumps(posts[:15], indent=1)}"""

    r = client.chat.completions.create(
        model="google/gemini-2.5-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = r.choices[0].message.content.strip()
    for fence in ("```json", "```"):
        if raw.startswith(fence):
            raw = raw[len(fence):]
    if raw.endswith("```"):
        raw = raw[:-3]
    result = json.loads(raw.strip())

    return jsonify({"posts": posts, "analysis": result})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json()
    topic = data.get("topic", "")
    angle = data.get("angle", "")
    fmt = data.get("format", "post")
    platform = data.get("platform", "linkedin")

    suggestion = {
        "title": topic,
        "angle": angle or topic,
        "recommended_format": fmt,
        "hashtags": data.get("hashtags", ["#WorkReadyAi", "#AI", "#Automation"]),
        "rationale": data.get("rationale", ""),
        "platforms": ["linkedin", "instagram", "facebook"],
    }

    copy = generate_post(suggestion, platform)
    return jsonify({"ok": True, "copy": copy, "platform": platform})


@app.route("/api/generate-image", methods=["POST"])
def api_generate_image():
    data = request.get_json()
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    result = generate_and_host(prompt)
    return jsonify(result)


@app.route("/api/publish", methods=["POST"])
def api_publish():
    data = request.get_json()
    platform = data.get("platform", "")
    copy = data.get("copy", "")
    image_url = data.get("image_url", "")

    if not copy:
        return jsonify({"error": "Copy text is required"}), 400

    if platform == "instagram":
        if not image_url:
            return jsonify({"error": "Instagram requires an image"}), 400
        result = create_instagram_image_post(image_url, copy)
        if not result.get("ok"):
            return jsonify({"error": f"Instagram failed at '{result.get('step')}': {result.get('error')}"}), 500
        post_id = result.get("media_id") or "published"
        return jsonify({"ok": True, "platform": "instagram", "post_id": post_id})

    elif platform == "linkedin":
        if image_url:
            result = create_image_post(copy, image_url)
        else:
            result = create_text_post(copy)
        if not result.get("ok"):
            return jsonify({"error": f"LinkedIn failed: {result.get('error')}"}), 500
        return jsonify({"ok": True, "platform": "linkedin", "post_id": result.get("id", "published")})

    elif platform == "facebook":
        result = create_facebook_post(copy)
        if not result.get("ok"):
            return jsonify({"error": f"Facebook failed: {result.get('error')}"}), 500
        return jsonify({"ok": True, "platform": "facebook", "post_id": result.get("post_id", "published")})

    else:
        return jsonify({"error": f"Unknown platform: {platform}"}), 400


@app.route("/.tmp/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(os.path.join(TMP_DIR, "images"), filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
