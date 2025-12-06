#!/usr/bin/env python3
"""
Patreon Scraper for Alexander Wales (or any creator)

This scraper downloads posts from a Patreon creator that you are subscribed to.
It requires your session_id cookie from an authenticated browser session.

Usage:
    1. Log into Patreon in your browser
    2. Get your session_id cookie (see get_session_id_instructions())
    3. Run: python patreon_scraper.py --session-id YOUR_SESSION_ID

The scraper outputs plain text suitable for text-to-speech (Speechify).
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
import html2text


# Alexander Wales' Patreon
DEFAULT_CREATOR_SLUG = "alexanderwales"
DEFAULT_OUTPUT_DIR = "output"

# Patreon API endpoints
PATREON_BASE_URL = "https://www.patreon.com"
PATREON_API_URL = f"{PATREON_BASE_URL}/api"


class PatreonScraper:
    """Scrape posts from a Patreon creator."""

    def __init__(self, session_id: str, creator_slug: str = DEFAULT_CREATOR_SLUG):
        self.session_id = session_id
        self.creator_slug = creator_slug
        self.session = requests.Session()
        self.session.cookies.set("session_id", session_id, domain=".patreon.com")
        self.session.headers.update({
            "User-Agent": "PatreonScraper - Personal Archive Tool",
            "Accept": "application/json",
        })
        self.campaign_id: Optional[str] = None

        # HTML to text converter for clean output
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.body_width = 0  # No wrapping

    def get_campaign_id(self) -> str:
        """Get the campaign ID for the creator."""
        if self.campaign_id:
            return self.campaign_id

        # Fetch the creator's page to get campaign ID
        url = f"{PATREON_BASE_URL}/{self.creator_slug}"
        response = self.session.get(url)
        response.raise_for_status()

        # Look for campaign ID in the page content
        # Patreon embeds JSON data in the page
        match = re.search(r'"campaign":\s*\{\s*"data":\s*\{\s*"id":\s*"(\d+)"', response.text)
        if match:
            self.campaign_id = match.group(1)
            return self.campaign_id

        # Alternative: look for campaign ID in API-style data
        match = re.search(r'"campaign_id":\s*(\d+)', response.text)
        if match:
            self.campaign_id = match.group(1)
            return self.campaign_id

        # Try fetching from the API directly
        match = re.search(r'patreon\.com/api/campaigns/(\d+)', response.text)
        if match:
            self.campaign_id = match.group(1)
            return self.campaign_id

        raise ValueError(f"Could not find campaign ID for {self.creator_slug}")

    def fetch_posts(self, limit: int = 100) -> list:
        """Fetch posts from the creator's campaign."""
        campaign_id = self.get_campaign_id()

        posts = []
        cursor = None

        while len(posts) < limit:
            # Use the internal API endpoint for posts
            url = f"{PATREON_API_URL}/posts"
            params = {
                "filter[campaign_id]": campaign_id,
                "filter[contains_exclusive_posts]": "true",
                "sort": "-published_at",
                "json-api-version": "1.0",
                "json-api-use-default-includes": "false",
                "include": "user,attachments,images",
                "fields[post]": "title,content,published_at,url,post_type,teaser_text",
                "fields[user]": "full_name",
                "page[count]": min(25, limit - len(posts)),
            }

            if cursor:
                params["page[cursor]"] = cursor

            response = self.session.get(url, params=params)

            if response.status_code == 401:
                raise ValueError("Session expired or invalid. Please get a new session_id.")
            elif response.status_code == 403:
                raise ValueError("Access forbidden. Make sure you're subscribed to this creator.")

            response.raise_for_status()
            data = response.json()

            for post_data in data.get("data", []):
                post = self._parse_post(post_data)
                if post:
                    posts.append(post)

            # Check for next page
            next_cursor = data.get("meta", {}).get("pagination", {}).get("cursors", {}).get("next")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

            # Rate limiting
            time.sleep(0.5)

        return posts[:limit]

    def _parse_post(self, post_data: dict) -> Optional[dict]:
        """Parse a post from the API response."""
        attrs = post_data.get("attributes", {})

        title = attrs.get("title", "Untitled")
        content_html = attrs.get("content", "")
        teaser = attrs.get("teaser_text", "")
        published_at = attrs.get("published_at", "")
        post_url = attrs.get("url", "")
        post_type = attrs.get("post_type", "")

        # Convert HTML content to plain text
        if content_html:
            content_text = self.h2t.handle(content_html).strip()
        else:
            content_text = teaser or ""

        # Parse date
        try:
            pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            date_str = pub_date.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            date_str = ""

        return {
            "id": post_data.get("id"),
            "title": title,
            "content": content_text,
            "date": date_str,
            "url": post_url,
            "type": post_type,
        }

    def fetch_single_post(self, post_id: str) -> Optional[dict]:
        """Fetch a single post by ID."""
        url = f"{PATREON_API_URL}/posts/{post_id}"
        params = {
            "json-api-version": "1.0",
            "fields[post]": "title,content,published_at,url,post_type",
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        return self._parse_post(data.get("data", {}))


def save_posts_as_text(posts: list, output_dir: str, single_file: bool = True):
    """Save posts as plain text files for text-to-speech."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if single_file:
        # Combine all posts into one file
        combined_path = output_path / "all_posts.txt"
        with open(combined_path, "w", encoding="utf-8") as f:
            for post in posts:
                f.write(f"{'='*60}\n")
                f.write(f"Title: {post['title']}\n")
                f.write(f"Date: {post['date']}\n")
                f.write(f"{'='*60}\n\n")
                f.write(post['content'])
                f.write("\n\n\n")
        print(f"Saved {len(posts)} posts to {combined_path}")
    else:
        # Save each post as a separate file
        for i, post in enumerate(posts, 1):
            safe_title = re.sub(r'[^\w\s-]', '', post['title'])[:50]
            filename = f"{post['date']}_{safe_title}.txt"
            filepath = output_path / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Title: {post['title']}\n")
                f.write(f"Date: {post['date']}\n\n")
                f.write(post['content'])

            print(f"Saved: {filepath}")


def get_session_id_instructions():
    """Print instructions for getting the session_id cookie."""
    instructions = """
How to get your Patreon session_id cookie:

1. Open your browser and go to https://www.patreon.com
2. Log in to your Patreon account
3. Open Developer Tools:
   - Chrome/Edge: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)
   - Firefox: Press F12 or Ctrl+Shift+I
4. Go to the "Application" tab (Chrome/Edge) or "Storage" tab (Firefox)
5. In the left sidebar, expand "Cookies" and click on "https://www.patreon.com"
6. Find the cookie named "session_id"
7. Copy the value (it's a long alphanumeric string)

Alternative method using browser console:
1. On any Patreon page, open Developer Tools
2. Go to the Console tab
3. Type: document.cookie.match(/session_id=([^;]+)/)?.[1]
4. Copy the output

Note: This session_id typically expires after about a month.
"""
    print(instructions)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Patreon posts for text-to-speech conversion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get instructions for finding your session_id
    python patreon_scraper.py --help-session

    # Scrape Alexander Wales' posts
    python patreon_scraper.py --session-id YOUR_SESSION_ID

    # Scrape a different creator
    python patreon_scraper.py --session-id YOUR_SESSION_ID --creator creatorname

    # Save as separate files instead of one combined file
    python patreon_scraper.py --session-id YOUR_SESSION_ID --separate-files
        """
    )

    parser.add_argument(
        "--session-id", "-s",
        help="Your Patreon session_id cookie value"
    )
    parser.add_argument(
        "--creator", "-c",
        default=DEFAULT_CREATOR_SLUG,
        help=f"Creator's Patreon slug (default: {DEFAULT_CREATOR_SLUG})"
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="Maximum number of posts to fetch (default: 50)"
    )
    parser.add_argument(
        "--separate-files",
        action="store_true",
        help="Save each post as a separate file instead of combining"
    )
    parser.add_argument(
        "--help-session",
        action="store_true",
        help="Show instructions for getting your session_id"
    )
    parser.add_argument(
        "--post-id",
        help="Fetch a single post by ID"
    )

    args = parser.parse_args()

    if args.help_session:
        get_session_id_instructions()
        return

    if not args.session_id:
        print("Error: --session-id is required")
        print("Use --help-session for instructions on finding your session_id")
        sys.exit(1)

    scraper = PatreonScraper(args.session_id, args.creator)

    try:
        print(f"Fetching campaign ID for {args.creator}...")
        campaign_id = scraper.get_campaign_id()
        print(f"Found campaign ID: {campaign_id}")

        if args.post_id:
            print(f"Fetching post {args.post_id}...")
            post = scraper.fetch_single_post(args.post_id)
            if post:
                print(f"\nTitle: {post['title']}")
                print(f"Date: {post['date']}")
                print(f"\n{post['content']}")
        else:
            print(f"Fetching up to {args.limit} posts...")
            posts = scraper.fetch_posts(limit=args.limit)
            print(f"Found {len(posts)} posts")

            if posts:
                save_posts_as_text(
                    posts,
                    args.output,
                    single_file=not args.separate_files
                )
                print(f"\nPosts saved to {args.output}/")
                print("You can now import these text files into Speechify!")
            else:
                print("No posts found. Make sure you're subscribed to this creator.")

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Network error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
