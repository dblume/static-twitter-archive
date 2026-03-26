#!/usr/bin/env python3
"""Generate a static website from a Twitter data archive.

Usage:
    pip install jinja2
    python generate.py
    # Then open output/index.html
"""

import argparse
import html
import json
import os
import re
import shutil
import stat
import sys
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from glob import glob
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    # Try Ubuntu system package location
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    from jinja2 import Environment, FileSystemLoader

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR           = Path(__file__).parent
TWEETS_JS          = BASE_DIR / 'tweets.js'
ACCOUNT_JS         = BASE_DIR / 'account.js'
LONGER_TWEETS_TXT  = BASE_DIR / 'longer_tweets.txt'
MEDIA_DIR          = BASE_DIR / 'tweets_media'
PROFILE_MEDIA      = BASE_DIR / 'profile_media'
TEMPLATES_DIR      = BASE_DIR / 'templates'
STATIC_DIR         = BASE_DIR / 'static'
OUTPUT_DIR         = BASE_DIR / 'output'
TWEETS_PER_PAGE    = 20

# ── Parse tweets.js ──────────────────────────────────────────────────────────
def load_tweets(tweets_js=None):
    if tweets_js is None:
        tweets_js = TWEETS_JS
    raw = tweets_js.read_text(encoding='utf-8')
    raw = re.sub(r'^\s*window\.YTD\.tweets\.part0\s*=\s*', '', raw)
    raw = raw.rstrip().rstrip(';')
    data = json.loads(raw)
    return [item['tweet'] for item in data]

# ── Parse account.js ─────────────────────────────────────────────────────────
def load_account():
    raw = ACCOUNT_JS.read_text(encoding='utf-8')
    raw = re.sub(r'^\s*window\.YTD\.account\.part0\s*=\s*', '', raw)
    raw = raw.rstrip().rstrip(';')
    data = json.loads(raw)
    return data[0]['account']

# ── Load longer_tweets.txt ───────────────────────────────────────────────────
def load_longer_tweets():
    """Return {tweet_id: text} from the tab-delimited longer_tweets.txt.

    Column 1 is the tweet URL; the ID is the trailing numeric segment.
    Column 2 is the candidate body text.
    Only loaded if the file exists.
    """
    if not LONGER_TWEETS_TXT.exists():
        return {}
    result = {}
    with LONGER_TWEETS_TXT.open(encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            parts = line.split('\t', 1)
            if len(parts) == 2:
                url, text = parts
                m = re.search(r'/(\d+)\s*$', url)
                if m:
                    result[m.group(1)] = text
    return result

# ── Date helpers ─────────────────────────────────────────────────────────────
def parse_date(date_str):
    return datetime.strptime(date_str, '%a %b %d %H:%M:%S %z %Y')

def format_date(dt):
    # 1:26 PM · Feb 26, 2024
    return dt.astimezone(ZoneInfo('US/Pacific')).strftime('%-I:%M %p · %b %-d, %Y %Z')

# ── Body HTML ────────────────────────────────────────────────────────────────
def make_body_html(tweet):
    """Convert tweet full_text to HTML with expanded URLs, hashtag/mention links."""
    text = tweet.get('full_text', '')
    entities = tweet.get('entities', {})

    # Media URLs appear as t.co links at end of text — we strip them
    # (we show images/videos separately)
    media_urls = set()
    for m in tweet.get('extended_entities', {}).get('media', []):
        media_urls.add(m.get('url', ''))
    for m in entities.get('media', []):
        media_urls.add(m.get('url', ''))

    # Build replacement spans: (start, end, html_string)
    spans = []

    for u in entities.get('urls', []):
        s, e = int(u['indices'][0]), int(u['indices'][1])
        if u['url'] in media_urls:
            spans.append((s, e, ''))
        else:
            href = html.escape(u['expanded_url'])
            disp = html.escape(u.get('display_url', u['expanded_url']))
            spans.append((s, e, f'<a href="{href}">{disp}</a>'))

    for m in entities.get('media', []):
        s, e = int(m['indices'][0]), int(m['indices'][1])
        spans.append((s, e, ''))

    for mention in entities.get('user_mentions', []):
        s, e = int(mention['indices'][0]), int(mention['indices'][1])
        sn = html.escape(mention['screen_name'])
        spans.append((s, e, f'<a href="https://x.com/{sn}">@{sn}</a>'))

    # Sort by start, discard overlapping spans (keep first)
    spans.sort(key=lambda x: x[0])
    filtered = []
    last_end = 0
    for s, e, repl in spans:
        if s >= last_end:
            filtered.append((s, e, repl))
            last_end = e

    # Reconstruct: full_text is already HTML-encoded, so plain text segments
    # are passed through as-is. Only entity-derived values (URLs, hashtags,
    # screen names) are escaped above where they are built.
    # Twitter indices are in Unicode code points.
    chars = list(text)
    result = []
    pos = 0
    for s, e, repl in filtered:
        if pos < s:
            result.append(''.join(chars[pos:s]))
        result.append(repl)
        pos = e
    if pos < len(chars):
        result.append(''.join(chars[pos:]))

    body = ''.join(result)
    for tag in entities.get('hashtags', []):
        t = html.escape(tag['text'])
        body = body.replace(f'#{tag["text"]}', f'<a href="https://x.com/hashtag/{t}">#{t}</a>')
    body = body.replace('\n', '<br>\n')
    return body

# ── Media ─────────────────────────────────────────────────────────────────────
def get_media_list(tweet):
    """Return list of {url, type, is_local} for a tweet's media."""
    tweet_id = tweet.get('id_str') or tweet.get('id', '')
    extended = tweet.get('extended_entities', {}).get('media', [])
    ent_media = tweet.get('entities', {}).get('media', [])
    all_media = extended if extended else ent_media

    media_list = []
    for m in all_media:
        mtype = m.get('type', 'photo')
        media_url_https = m.get('media_url_https', '')

        if media_url_https:
            cdn_name = Path(media_url_https).name  # e.g. "AbCdEfG.jpg"
            local_path = MEDIA_DIR / f'{tweet_id}-{cdn_name}'
            if local_path.exists():
                media_list.append({
                    'url': f'tweets_media/{tweet_id}-{cdn_name}',
                    'type': mtype,
                    'is_local': True,
                })
                continue
            # CDN name didn't match directly — fall back to glob
            found = sorted(glob(str(MEDIA_DIR / f'{tweet_id}-*')))
            if found:
                idx = len(media_list)
                if idx < len(found):
                    fname = Path(found[idx]).name
                    media_list.append({'url': f'tweets_media/{fname}', 'type': mtype, 'is_local': True})
                    continue

        # No local file — use external CDN URL
        media_list.append({'url': media_url_https or m.get('media_url', ''), 'type': mtype, 'is_local': False})

    return media_list

# ── Preprocess ────────────────────────────────────────────────────────────────
def _candidate_spans_align(orig_text, entities, candidate):
    """Return True if all entity index spans in orig_text still match in candidate."""
    all_spans = (
        [(int(m['indices'][0]), int(m['indices'][1])) for m in entities.get('user_mentions', [])]
        + [(int(u['indices'][0]), int(u['indices'][1])) for u in entities.get('urls', [])]
        + [(int(t['indices'][0]), int(t['indices'][1])) for t in entities.get('hashtags', [])]
        + [(int(m['indices'][0]), int(m['indices'][1])) for m in entities.get('media', [])]
    )
    for s, e in all_spans:
        if e > len(candidate) or candidate[s:e] != orig_text[s:e]:
            return False
    return True

def preprocess_tweets(raw_tweets, longer_tweets=None):
    if longer_tweets is None:
        longer_tweets = {}
    tweets = []
    for raw in raw_tweets:
        try:
            dt = parse_date(raw['created_at'])
        except Exception:
            dt = datetime.min.replace(tzinfo=None)

        tweet_id = raw.get('id_str') or raw.get('id', '')

        # Substitute longer body text when available
        candidate = longer_tweets.get(tweet_id, '')
        orig_text = raw.get('full_text', '')
        if (candidate and '<' not in candidate and len(candidate) > len(orig_text)
                and _candidate_spans_align(orig_text, raw.get('entities', {}), candidate)):
            raw = dict(raw, full_text=candidate)

        tweets.append({
            'id':                    tweet_id,
            'date_display':          format_date(dt),
            'dt':                    dt,
            'body_html':             make_body_html(raw),
            'is_rt':                 raw.get('full_text', '').startswith('RT @'),
            'media':                 get_media_list(raw),
            'favorite_count':        int(raw.get('favorite_count', 0) or 0),
            'retweet_count':         int(raw.get('retweet_count', 0) or 0),
            'in_reply_to_id':        raw.get('in_reply_to_status_id_str') or raw.get('in_reply_to_status_id'),
            'in_reply_to_screen_name': raw.get('in_reply_to_screen_name', ''),
            'in_reply_to_local':     False,
        })

    tweets.sort(key=lambda t: t['dt'], reverse=True)
    return tweets

def build_reply_map(tweets):
    tweet_ids = {t['id'] for t in tweets}
    reply_map = {}
    for t in tweets:
        pid = t['in_reply_to_id']
        if pid:
            t['in_reply_to_local'] = pid in tweet_ids
            reply_map.setdefault(pid, []).append(t)
    return reply_map

# ── Pagination helper ─────────────────────────────────────────────────────────
def make_page_range(current, total, window=2):
    pages = set()
    pages.add(1)
    pages.add(total)
    for p in range(max(1, current - window), min(total, current + window) + 1):
        pages.add(p)
    sorted_pages = sorted(pages)
    result = []
    prev = None
    for p in sorted_pages:
        if prev is not None and p - prev > 1:
            result.append(-1)  # ellipsis
        result.append(p)
        prev = p
    return result

# ── Output setup ──────────────────────────────────────────────────────────────
def setup_output():
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / 'page').mkdir(exist_ok=True)
    (OUTPUT_DIR / 'status').mkdir(exist_ok=True)
    # Remove legacy tweet/ dir if it exists from an older generation
    old_tweet_dir = OUTPUT_DIR / 'tweet'
    if old_tweet_dir.exists():
        shutil.rmtree(old_tweet_dir)

    out_static = OUTPUT_DIR / 'static'
    if out_static.exists():
        shutil.rmtree(out_static)
    shutil.copytree(STATIC_DIR, out_static)

    # Copy avatar from profile_media into static/
    avatar_src = PROFILE_MEDIA / 'avatar_round_40.png'
    if avatar_src.exists():
        shutil.copy2(avatar_src, out_static / 'avatar.png')

    # Ensure all static files are world-readable
    for f in out_static.iterdir():
        if f.is_file():
            f.chmod(f.stat().st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    link = OUTPUT_DIR / 'tweets_media'
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to('../tweets_media')

# ── Render index pages ────────────────────────────────────────────────────────
def render_index_pages(env, tweets):
    tmpl = env.get_template('index.html')
    total = len(tweets)
    total_pages = (total + TWEETS_PER_PAGE - 1) // TWEETS_PER_PAGE

    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * TWEETS_PER_PAGE
        chunk = tweets[start:start + TWEETS_PER_PAGE]
        root = '' if page_num == 1 else '../'
        ctx = {
            'tweets':           chunk,
            'page_num':         page_num,
            'total_pages':      total_pages,
            'page_range':       make_page_range(page_num, total_pages),
            'root':             root,
            'prev_last_id':     tweets[start - 1]['id'] if page_num > 1 else None,
        }
        html_out = tmpl.render(**ctx)
        if page_num == 1:
            (OUTPUT_DIR / 'index.html').write_text(html_out, encoding='utf-8')
        else:
            (OUTPUT_DIR / 'page' / f'{page_num}.html').write_text(html_out, encoding='utf-8')

        if page_num % 50 == 0:
            print(f'  index page {page_num}/{total_pages}')

    print(f'  {total_pages} index pages')

# ── Render tweet pages ────────────────────────────────────────────────────────
def render_tweet_pages(env, tweets, reply_map):
    tmpl = env.get_template('tweet.html')
    for i, tweet in enumerate(tweets):
        replies = reply_map.get(tweet['id'], [])
        page_num = i // TWEETS_PER_PAGE + 1
        if page_num == 1:
            back_url = '../index.html#' + tweet['id']
        else:
            back_url = f'../page/{page_num}.html#' + tweet['id']
        ctx = {
            'tweet':      tweet,
            'replies':    replies,
            'prev_id':    tweets[i - 1]['id'] if i > 0 else None,
            'next_id':    tweets[i + 1]['id'] if i < len(tweets) - 1 else None,
            'author':     env.globals['screen_name'],
            'root':       '../',
            'back_url':   back_url,
        }
        html_out = tmpl.render(**ctx)
        (OUTPUT_DIR / 'status' / tweet["id"]).write_text(html_out, encoding='utf-8')
        if (i + 1) % 500 == 0:
            print(f'  tweet pages {i+1}/{len(tweets)}')

    print(f'  {len(tweets)} tweet pages')

# ── Render search page ────────────────────────────────────────────────────────
def render_search_page(env, tweets):
    tmpl = env.get_template('search.html')
    ctx = {'tweet_count': len(tweets), 'root': ''}
    (OUTPUT_DIR / 'search.html').write_text(tmpl.render(**ctx), encoding='utf-8')

# ── Build search index ────────────────────────────────────────────────────────
def build_search_index(tweets):
    index = []
    for t in tweets:
        text = re.sub(r'<[^>]+>', '', t['body_html'])
        text = html.unescape(text)
        index.append({
            'id':       t['id'],
            'text':     text,
            'date':     t['date_display'],
            'is_rt':    t['is_rt'],
            'has_media': bool(t['media']),
        })
    out = json.dumps(index, separators=(',', ':'), ensure_ascii=False)
    (OUTPUT_DIR / 'search-index.json').write_text(out, encoding='utf-8')
    size_kb = len(out.encode('utf-8')) / 1024
    print(f'  {len(index)} tweets, {size_kb:.0f} KB')

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Generate a static website from a Twitter data archive.')
    parser.add_argument('filename', nargs='?', default='tweets.js',
                        help='Path to tweets JS file (default: tweets.js)')
    args = parser.parse_args()
    tweets_js = BASE_DIR / args.filename

    account = load_account()
    screen_name  = account['username']
    display_name = account['accountDisplayName']
    site_title   = f"{screen_name}'s Tweets"

    print(f'Parsing {args.filename}...')
    raw_tweets = load_tweets(tweets_js)
    print(f'  {len(raw_tweets)} tweets loaded')

    longer_tweets = load_longer_tweets()
    if longer_tweets:
        print(f'  {len(longer_tweets)} entries in longer_tweets.txt')

    print('Preprocessing...')
    tweets = preprocess_tweets(raw_tweets, longer_tweets)
    reply_map = build_reply_map(tweets)
    print(f'  {sum(t["is_rt"] for t in tweets)} retweets, '
          f'{sum(bool(t["media"]) for t in tweets)} with media, '
          f'{sum(bool(t["in_reply_to_id"]) for t in tweets)} replies')

    print('Setting up output/...')
    setup_output()

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
    )
    env.globals['display_name'] = display_name
    env.globals['screen_name']  = screen_name
    env.globals['site_title']   = site_title

    print('Rendering index pages...')
    render_index_pages(env, tweets)

    print('Rendering tweet pages...')
    render_tweet_pages(env, tweets, reply_map)

    print('Rendering search page...')
    render_search_page(env, tweets)

    print('Building search index...')
    build_search_index(tweets)

    print(f'\nDone. Open: output/index.html')

if __name__ == '__main__':
    main()
