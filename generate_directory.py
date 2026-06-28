import os
import sys
import requests
import feedparser
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from collections import defaultdict

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════

CREDENTIALS_FILE = "credentials.json"
SHEET_NAME       = "AniManga Index - Creator Submission Form (Responses)"  # exact name from Google Drive

# NOTE: Replace all placeholders below with your actual details
YOUR_NAME         = "N Senpai"               # e.g. "N Senpai"
YOUR_PUBLICATION  = "Weekly AniManga Index"
YOUR_SUBSTACK_URL = "https://nsenpai.substack.com/"       # e.g. "https://yourname.substack.com"
YOUR_RSS_FEED     = "https://nsenpai.substack.com/feed"       # e.g. "https://yourname.substack.com/feed"
YOUR_BANNER_PATH  = "banner.png"                   # banner filename, place in same folder as this script

OUTPUT_FILE = "index.html"

# Column map — must match your Google Sheet headers exactly
COLUMN_MAP = {
    "profile_name":     "What's your Profile Name?",
    "publication_name": "What's your Publication Name?",
    "publication_url":  "What's your Substack URL(username.substack.com)",
    "main_category":    "Select your Primary publication category",
    "second_category":  "Select your Secondary publication category",
    "country":          "Which Country do you live in?",
    "description":      "Please give a brief description of your publication",
    "mature":           "Does your work contain mature themes (e.g., substance use, explicit language, non-sexual violence)",
}

MATURE_YES_VALUE = "Yes"

# Category names exactly as they appear in your sheet, mapped to short button labels
CATEGORIES = {
    "Anime and Manga Commentary & Analysis":  "Anime & Manga",
    "Artists & Illustrators":               "Artists",
    "Original Long Form Story Creators":    "Long Form Stories",
    "Original Short Form Story Creators":   "Short Form Stories",
    "Fandom & Culture":                     "Fandom",
    "Industry & Meta":                      "Industry",
    "Gaming":                               "Gaming",
    "Film & TV Commentary & Analysis":      "Film & TV",
}

# ══════════════════════════════════════════════════════════════════════════
# DO NOT EDIT BELOW THIS LINE
# ══════════════════════════════════════════════════════════════════════════


RSS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def normalize_url(url):
    url = str(url).strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    return url


def fetch_latest_post(rss_url):
    try:
        response = requests.get(rss_url, headers=RSS_HEADERS, timeout=10)
        feed     = feedparser.parse(response.content)
        if feed.entries:
            entry = feed.entries[0]
            return {
                "title": entry.get("title", "").strip(),
                "url":   entry.get("link", "").strip(),
            }
    except Exception:
        pass
    return None


def generate_html(writers_by_category, latest_post, total_writers):
    # ── Filter buttons ────────────────────────────────────────────────────
    def cat_key(name):
        return name.replace("&", "and").replace(" ", "-").lower()

    filter_buttons = '      <button class="filter-btn active" data-category="all">All</button>\n'
    for full_name, short_label in CATEGORIES.items():
        key = cat_key(full_name)
        filter_buttons += f'      <button class="filter-btn" data-category="{key}">{short_label}</button>\n'

    # ── Writer cards ──────────────────────────────────────────────────────
    # Use sanitized category keys in data-category to avoid & issues in HTML attributes
    def cat_key(name):
        return name.replace("&", "and").replace(" ", "-").lower()

    all_cards = ""
    for full_name, writers in writers_by_category.items():
        for w in writers:
            url        = normalize_url(w["publication_url"])
            mature_tag = ' <span class="mature-tag">MATURE</span>' if w["mature"] else ""
            country    = f'<span class="writer-country">{w["country"]}</span>' if w.get("country") else ""
            desc       = f'<p class="writer-desc">{w["description"]}</p>' if w.get("description") else ""
            key        = cat_key(full_name)

            all_cards += f'''
    <div class="writer-card" data-category="{key}" data-url="{url}" onclick="this.classList.toggle('expanded')">
      <div class="card-top">
        <div>
          <a href="{url}" target="_blank" class="writer-name" onclick="event.stopPropagation()">{w["profile_name"]}</a>{mature_tag}
          {country}
        </div>
        <a href="{url}" target="_blank" class="pub-name" onclick="event.stopPropagation()">{w["publication_name"]}</a>
      </div>
      <div class="writer-desc-wrap">{desc}</div>
      <div class="cat-label">{full_name}</div>
    </div>'''

    # ── Latest post banner ────────────────────────────────────────────────
    if latest_post:
        latest_html = f'''
  <a href="{latest_post["url"]}" target="_blank" class="latest-post">
    <span class="latest-eyebrow">Latest from the curator</span>
    <span class="latest-title">{latest_post["title"]}</span>
    <span class="latest-arrow">&#8594;</span>
  </a>'''
    else:
        latest_html = ""

    updated = datetime.now().strftime("%B %d, %Y")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{YOUR_PUBLICATION} — Writer Directory</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap" rel="stylesheet">
  <style>
    :root {{
      --teal:       #0d9488;
      --teal-light: #14b8a6;
      --teal-dark:  #0f766e;
      --bg:         #fafafa;
      --bg-card:    #ffffff;
      --border:     #e5e7eb;
      --text:       #111827;
      --text-muted: #6b7280;
      --text-dim:   #9ca3af;
      --mature:     #d97706;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'DM Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}

    /* ── Header ── */
    .header {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 1.5rem 1.5rem 1.25rem;
      border-bottom: 2px solid var(--teal);
    }}

    .pub-title {{
      font-family: 'Playfair Display', serif;
      font-size: 2.5rem;
      font-weight: 700;
      color: var(--text);
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .pub-title:hover {{ color: var(--teal); }}

    .pub-logo {{
      width: 80px;
      height: 80px;
      object-fit: contain;
      border-radius: 6px;
      flex-shrink: 0;
    }}

    .header-left {{
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}

    .header-meta {{
      font-size: 0.98rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }}

    .digest-link-text {{
      font-size: 1rem;
      color: var(--text-muted);
      margin-top: 0.35rem;
    }}

    .digest-link {{
      color: var(--teal);
      text-decoration: none;
      font-weight: 600;
      font-size: 1rem;
    }}

    .digest-link:hover {{ text-decoration: underline; }}

    /* ── Latest post ── */
    .latest-post {{
      display: flex;
      align-items: center;
      gap: 1rem;
      max-width: 1100px;
      margin: 1rem auto 0;
      padding: 0.875rem 1.25rem;
      background: var(--teal);
      border-radius: 8px;
      text-decoration: none;
      transition: background 0.2s;
    }}

    .latest-post:hover {{ background: var(--teal-dark); }}

    .latest-eyebrow {{
      font-size: 0.7rem;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #ccfbf1;
      white-space: nowrap;
    }}

    .latest-title {{
      font-family: 'Playfair Display', serif;
      font-size: 0.95rem;
      color: #ffffff;
      flex: 1;
    }}

    .latest-arrow {{
      color: #ccfbf1;
      font-size: 1.1rem;
    }}

    /* ── Divider ── */
    .divider {{
      max-width: 1100px;
      margin: 1.5rem auto 0;
      border: none;
      border-top: 1px solid var(--border);
    }}

    /* ── Filters ── */
    .filters {{
      max-width: 1100px;
      margin: 1.25rem auto 0;
      padding: 0 1.5rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }}

    .filter-btn {{
      padding: 0.4rem 0.9rem;
      border-radius: 99px;
      border: 1.5px solid var(--border);
      background: var(--bg-card);
      color: var(--text-muted);
      font-family: 'DM Sans', sans-serif;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }}

    .filter-btn:hover {{
      border-color: var(--teal);
      color: var(--teal);
    }}

    .filter-btn.active {{
      background: var(--teal);
      border-color: var(--teal);
      color: #ffffff;
    }}

    /* ── Grid ── */
    .grid {{
      max-width: 1100px;
      margin: 1.25rem auto 3rem;
      padding: 0 1.5rem;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1rem;
    }}

    /* ── Writer card ── */
    .writer-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.75rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      transition: box-shadow 0.2s, border-color 0.2s;
      cursor: pointer;
    }}

    .writer-card.hidden {{ display: none; }}

    .writer-card:hover {{
      border-color: var(--teal-light);
      box-shadow: 0 4px 16px rgba(13, 148, 136, 0.08);
    }}

    .writer-card.hidden {{ display: none; }}

    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.5rem;
    }}

    .writer-name {{
      font-family: 'Playfair Display', serif;
      font-size: 1rem;
      font-weight: 600;
      color: var(--text);
      text-decoration: none;
    }}

    .writer-name:hover {{ color: var(--teal); }}

    .mature-tag {{
      font-size: 0.65rem;
      font-weight: 600;
      color: var(--mature);
      border: 1px solid var(--mature);
      border-radius: 4px;
      padding: 0.1rem 0.35rem;
      vertical-align: middle;
      margin-left: 0.3rem;
    }}

    .writer-country {{
      display: block;
      font-size: 0.75rem;
      color: var(--text-dim);
      margin-top: 0.15rem;
    }}

    .pub-name {{
      font-size: 0.78rem;
      font-weight: 500;
      color: var(--teal);
      text-decoration: none;
      text-align: right;
      white-space: nowrap;
    }}

    .pub-name:hover {{ color: var(--teal-dark); text-decoration: underline; }}

    .writer-desc-wrap {{
      display: none;
    }}

    .writer-card.expanded .writer-desc-wrap {{
      display: block;
    }}

    .writer-desc {{
      font-size: 0.82rem;
      color: var(--text-muted);
      line-height: 1.55;
      padding-top: 0.35rem;
    }}

    .cat-label {{
      font-size: 0.7rem;
      color: var(--text-dim);
      margin-top: auto;
      padding-top: 0.25rem;
      border-top: 1px solid var(--border);
    }}

    /* ── Footer ── */
    .footer {{
      text-align: center;
      padding: 1.5rem;
      font-size: 0.75rem;
      color: var(--text-dim);
      border-top: 1px solid var(--border);
    }}

    .footer a {{ color: var(--teal); text-decoration: none; }}
    .footer a:hover {{ text-decoration: underline; }}

    /* ── No results ── */
    .no-results {{
      grid-column: 1 / -1;
      text-align: center;
      padding: 3rem;
      color: var(--text-muted);
      font-size: 0.9rem;
    }}

    /* ── Responsive ── */
    @media (max-width: 600px) {{
      .header {{ flex-direction: column; }}

      .latest-post {{ flex-wrap: wrap; }}
      .latest-eyebrow {{ width: 100%; }}
    }}
  </style>
</head>
<body>

  <div class="header">
    <div class="header-left">
      <a href="{YOUR_SUBSTACK_URL}" target="_blank" class="pub-title">
        <img src="{YOUR_BANNER_PATH}" alt="{YOUR_PUBLICATION}" class="pub-logo">
        {YOUR_PUBLICATION}
      </a>
      <p class="header-meta">{total_writers} writers listed &nbsp;|&nbsp; updated {updated}</p>
      <p class="digest-link-text">Read the latest digest on <a href="{YOUR_SUBSTACK_URL}" target="_blank" class="digest-link">Substack &rarr;</a></p>
    </div>
  </div>

  {latest_html}

  <hr class="divider">

  <div class="filters">
    {filter_buttons}
  </div>

  <div class="grid" id="writer-grid">
    {all_cards}
    <div id="no-results" style="display:none;grid-column:1/-1;text-align:center;padding:3rem;color:#6b7280;font-size:0.9rem;">No writers found in this category yet.</div>
  </div>

  <div class="footer">
      <a href="{YOUR_SUBSTACK_URL}" target="_blank">{YOUR_PUBLICATION}</a> &nbsp;|&nbsp;
      Updated weekly &nbsp;|&nbsp; {updated} &nbsp;|&nbsp;
      <a href="https://ko-fi.com/nsenpaiwrites" target="_blank">Buy me a coffee☕</a>
    </div>

  <script>
    const btns  = document.querySelectorAll('.filter-btn');
    const cards = document.querySelectorAll('.writer-card');
    const noRes = document.getElementById('no-results');

    btns.forEach(btn => {{
      btn.addEventListener('click', () => {{
        btns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const cat = btn.dataset.category;
        let visible = 0;
        const seenUrls = new Set();

        cards.forEach(card => {{
          const match = cat === 'all' || card.dataset.category === cat;
          if (match) {{
            const url = card.dataset.url;
            if (cat === 'all' && seenUrls.has(url)) {{
              card.style.display = 'none';
            }} else {{
              card.style.display = 'flex';
              seenUrls.add(url);
              visible++;
            }}
          }} else {{
            card.style.display = 'none';
          }}
        }});

        if (cat === 'all') {{
          noRes.style.display = 'none';
        }} else {{
          noRes.style.display = visible > 0 ? 'none' : 'block';
        }}
      }});
    }});

    // trigger All on load to deduplicate initial view
    document.querySelector('.filter-btn[data-category="all"]').click();
  </script>

</body>
</html>'''


def main():
    print("=" * 55)
    print("  Directory Generator")
    print("=" * 55)
    print()

    # ── Auth ──────────────────────────────────────────────────────────────
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(creds)
    except FileNotFoundError:
        print(f"❌ credentials.json not found. Current folder: {os.getcwd()}")
        sys.exit(1)

    try:
        sheet = client.open(SHEET_NAME).sheet1
    except Exception:
        print(f"❌ Could not open sheet: '{SHEET_NAME}'")
        sys.exit(1)

    rows = sheet.get_all_records()
    print(f"✅ Connected. Found {len(rows)} writer(s).")

    # ── Build writers by category ─────────────────────────────────────────
    writers_by_category = defaultdict(list)

    for r in rows:
        url = r.get(COLUMN_MAP.get("publication_url", ""), "")
        if not url:
            continue

        # skip inactive writers
        active_value = str(r.get("Active", "")).strip().lower()
        if "Active" in r and active_value == "no":
            continue

        mature = r.get(COLUMN_MAP.get("mature", ""), "") == MATURE_YES_VALUE

        writer = {
            "profile_name":     r.get(COLUMN_MAP.get("profile_name", ""), ""),
            "publication_name": r.get(COLUMN_MAP.get("publication_name", ""), ""),
            "publication_url":  str(url).strip(),
            "country":          r.get(COLUMN_MAP.get("country", ""), "") if "country" in COLUMN_MAP else "",
            "description":      r.get(COLUMN_MAP.get("description", ""), "") if "description" in COLUMN_MAP else "",
            "mature":           mature,
        }

        # add under main category
        main_cat = r.get(COLUMN_MAP.get("main_category", ""), "").strip()
        if main_cat:
            writers_by_category[main_cat].append(writer)

        # add under second category if exists
        second_cat = r.get(COLUMN_MAP.get("second_category", ""), "").strip()
        if second_cat and second_cat != main_cat:
            writers_by_category[second_cat].append(writer)

    print("\n📊 Category breakdown:")
    for cat, ws in writers_by_category.items():
        print(f"  {cat}: {len(ws)} writer(s)")
    print()

    print("\n🔍 Second category debug:")
    for r in rows[:3]:
        second_key = COLUMN_MAP.get("second_category", "NOT IN MAP")
        second_val = r.get(second_key, "KEY NOT FOUND")
        print(f"  key used: '{second_key}'")
        print(f"  value: '{second_val}'")
        print()

    total_writers = len(rows)
    print(f"✅ Writers mapped to categories.")

    # ── Fetch your latest post ────────────────────────────────────────────
    print(f"Fetching your latest post...")
    latest_post = fetch_latest_post(YOUR_RSS_FEED)
    if latest_post:
        print(f"✅ Latest post: {latest_post['title']}")
    else:
        print(f"⚠️  Could not fetch latest post. Continuing without it.")

    # ── Generate HTML ─────────────────────────────────────────────────────
    html = generate_html(writers_by_category, latest_post, total_writers)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Directory saved to {OUTPUT_FILE}")
    print()
    print("Open index.html in your browser to preview.")
    print("=" * 55)


if __name__ == "__main__":
    main()
