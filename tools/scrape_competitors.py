from apify_client import ApifyClient
import os

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))


def scrape_instagram(handles):
    """handles = list of strings, no @ prefix"""
    all_posts = []
    for handle in handles:
        run = client.actor("apify/instagram-scraper").call(run_input={
            "usernames": [handle],
            "resultsType": "posts",
            "resultsLimit": 20,
            "addParentData": False,
        })
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            # Skip error items returned by Apify (e.g. no_items, private account)
            if item.get("error") or not item.get("username"):
                continue
            all_posts.append({
                "platform": "instagram",
                "username": item.get("username", ""),
                "caption": item.get("caption", ""),
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0),
                "format": item.get("type", "Image"),
                "timestamp": item.get("timestamp", ""),
                "hashtags": item.get("hashtags", []),
            })
    return all_posts


def scrape_linkedin(urls):
    """urls = list of full LinkedIn company/profile URLs"""
    all_posts = []
    for url in urls:
        run = client.actor("harvestapi/linkedin-company-posts").call(run_input={
            "startUrls": [{"url": url}],
            "maxItems": 15,
        })
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            all_posts.append({
                "platform": "linkedin",
                "author": item.get("author", {}).get("name", ""),
                "text": item.get("text", ""),
                "likes": item.get("numLikes", 0),
                "comments": item.get("numComments", 0),
                "format": item.get("type", "text"),
                "timestamp": item.get("postedAt", ""),
                "url": item.get("url", ""),
            })
    return all_posts
