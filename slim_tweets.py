#!/usr/bin/env python3
"""Remove unused fields from tweets.js and write slimmed JSON to stdout.

Usage:
    python slim_tweets.py > tweets_slim.js
"""

import json
import re
import sys
from pathlib import Path

INPUT_JS = Path(__file__).parent / 'tweets.js'

# Top-level tweet fields not read by generate.py
REMOVE_TOP = {
    'display_text_range',
    'edit_info',
    'favorited',
    'in_reply_to_user_id',
    'in_reply_to_user_id_str',
    'lang',
    'possibly_sensitive',
    'retweeted',
    'source',
    'truncated',
}

# Within entities.user_mentions, only screen_name + indices are used
KEEP_MENTION_FIELDS = {'screen_name', 'indices'}

# Within media items, only these fields are used
KEEP_MEDIA_FIELDS = {'type', 'media_url_https', 'media_url', 'url', 'indices'}

# entities.symbols is never used
REMOVE_ENTITY_KEYS = {'symbols'}


def slim_tweet(tweet: dict) -> dict:
    t = {k: v for k, v in tweet.items() if k not in REMOVE_TOP}

    if 'entities' in t:
        ent = dict(t['entities'])
        for key in REMOVE_ENTITY_KEYS:
            ent.pop(key, None)
        if 'user_mentions' in ent:
            ent['user_mentions'] = [
                {k: v for k, v in m.items() if k in KEEP_MENTION_FIELDS}
                for m in ent['user_mentions']
            ]
        if 'media' in ent:
            ent['media'] = [
                {k: v for k, v in m.items() if k in KEEP_MEDIA_FIELDS}
                for m in ent['media']
            ]
        t['entities'] = ent

    if 'extended_entities' in t:
        ext = dict(t['extended_entities'])
        if 'media' in ext:
            ext['media'] = [
                {k: v for k, v in m.items() if k in KEEP_MEDIA_FIELDS}
                for m in ext['media']
            ]
        t['extended_entities'] = ext

    return t


def main():
    raw = INPUT_JS.read_text(encoding='utf-8')
    raw_stripped = re.sub(r'^\s*window\.YTD\.tweets\.part0\s*=\s*', '', raw)
    raw_stripped = raw_stripped.rstrip().rstrip(';')
    data = json.loads(raw_stripped)

    slimmed = [{'tweet': slim_tweet(item['tweet'])} for item in data]

    out = 'window.YTD.tweets.part0 = ' + json.dumps(slimmed, indent=1, separators=(',', ':'), ensure_ascii=False) + ';'

    before_kb = len(raw.encode('utf-8')) / 1024
    after_kb  = len(out.encode('utf-8')) / 1024
    saving_pct = 100 * (1 - after_kb / before_kb)
    print(f'# {len(slimmed)} tweets  |  before: {before_kb:,.0f} KB  after: {after_kb:,.0f} KB  ({saving_pct:.0f}% smaller)', file=sys.stderr)

    sys.stdout.write(out)


if __name__ == '__main__':
    main()
