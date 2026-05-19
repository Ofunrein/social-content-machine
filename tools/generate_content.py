import os
import openai
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = openai.OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

PLATFORM_PROMPTS = {
    "linkedin": """Write a LinkedIn post about: {title}
Angle: {angle}
Format: {format}
Hashtags to include: {hashtags}
Context: {rationale}

Write in a professional but engaging tone. Keep it under 1300 characters. Include a hook in the first line. End with a call-to-action or question.""",

    "instagram": """Write an Instagram caption about: {title}
Angle: {angle}
Format: {format}
Hashtags to include: {hashtags}
Context: {rationale}

Write in a casual, engaging tone. Keep the main caption under 500 characters. Put hashtags at the end separated by a line break.""",

    "facebook": """Write a Facebook post about: {title}
Angle: {angle}
Format: {format}
Hashtags to include: {hashtags}
Context: {rationale}

Write in a conversational, community-focused tone. Keep it under 800 characters. Include a question or call-to-action to encourage engagement.""",
}


def generate_post(suggestion: dict, platform: str) -> str:
    prompt = PLATFORM_PROMPTS.get(platform, PLATFORM_PROMPTS["linkedin"]).format(
        title=suggestion.get("title", ""),
        angle=suggestion.get("angle", ""),
        format=suggestion.get("recommended_format", "post"),
        hashtags=", ".join(suggestion.get("hashtags", [])),
        rationale=suggestion.get("rationale", ""),
    )
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4-6",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()
