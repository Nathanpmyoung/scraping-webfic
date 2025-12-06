# Patreon Scraper for Web Fiction

Scrape Patreon posts (including patron-only content you're subscribed to) and convert them to plain text for text-to-speech apps like Speechify.

## Setup

```bash
pip install -r requirements.txt
```

## Getting Your Session ID

Since you want to access patron-only posts, you need to authenticate using your browser's session cookie:

1. **Log into Patreon** at https://www.patreon.com
2. **Open Developer Tools** (F12 or Ctrl+Shift+I)
3. **Go to Application tab** → Cookies → patreon.com
4. **Find `session_id`** and copy its value

Or use the console method:
```javascript
document.cookie.match(/session_id=([^;]+)/)?.[1]
```

## Usage

### Scrape Alexander Wales' Posts

```bash
python patreon_scraper.py --session-id YOUR_SESSION_ID
```

### Options

```bash
# Scrape different creator
python patreon_scraper.py -s YOUR_SESSION_ID --creator othercreator

# Limit number of posts
python patreon_scraper.py -s YOUR_SESSION_ID --limit 100

# Save as separate files (one per post)
python patreon_scraper.py -s YOUR_SESSION_ID --separate-files

# Custom output directory
python patreon_scraper.py -s YOUR_SESSION_ID --output my_downloads
```

### Output

By default, all posts are saved to `output/all_posts.txt` - a single file you can import directly into Speechify.

Use `--separate-files` to save each post individually (useful for organizing by chapter).

## Notes

- You can only download content you have access to (i.e., posts at your subscription tier)
- Session IDs expire after about a month
- This is for personal archival use only
