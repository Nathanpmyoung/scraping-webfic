#!/usr/bin/env python3
"""
Fetch full content for Thresholder chapters 88-120
"""

import json
import re
import time
from patreon_scraper import PatreonScraper, save_posts_as_text

def main():
    session_id = "b6e0d6e9-319f-4461-919b-e095d8ac7ab8"
    scraper = PatreonScraper(session_id, "alexanderwales")

    print("Step 1: Fetching posts list to find chapters 88-120...")
    all_posts = scraper.fetch_posts(limit=200, full_content=False)

    # Filter for chapters 88-120
    target_posts = []
    for post in all_posts:
        match = re.search(r'Thresholder, ch (\d+)(?:-(\d+))?', post['title'])
        if match:
            ch_start = int(match.group(1))
            ch_end = int(match.group(2)) if match.group(2) else ch_start

            if 88 <= ch_start <= 120:
                target_posts.append(post)

    print(f"Found {len(target_posts)} posts for chapters 88-120")

    # Sort by chapter number
    def get_chapter_num(post):
        match = re.search(r'ch (\d+)', post['title'])
        return int(match.group(1)) if match else 999

    target_posts.sort(key=get_chapter_num)

    print("\nStep 2: Fetching full content for each chapter...")
    for i, post in enumerate(target_posts, 1):
        if post.get('url'):
            try:
                print(f"  [{i}/{len(target_posts)}] {post['title']}")
                full_post = scraper.fetch_post_from_url(post['url'])
                if full_post and full_post.get('content'):
                    post['content'] = full_post['content']
                    print(f"      ✓ Fetched {len(full_post['content'])} characters")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"      ✗ Error: {e}")

    print("\nStep 3: Saving to file...")
    save_posts_as_text(target_posts, "output", single_file=True)

    # Also save to dedicated file
    with open('output/thresholder_ch88-120_full.txt', 'w') as f:
        for post in target_posts:
            f.write('=' * 60 + '\n')
            f.write(f"Title: {post['title']}\n")
            f.write(f"Date: {post['date']}\n")
            f.write('=' * 60 + '\n\n')
            f.write(post['content'])
            f.write('\n\n\n')

    print(f"\n✓ Saved {len(target_posts)} chapters to output/thresholder_ch88-120_full.txt")

if __name__ == '__main__':
    main()
