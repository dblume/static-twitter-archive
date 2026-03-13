![License](https://img.shields.io/badge/license-None-blue.svg)
![python3.x](https://img.shields.io/badge/python-3.x-green.svg)
![AI](https://img.shields.io/badge/AI-Mostly-yellow.svg)

# Static Twitter Archive

A static site generator that turns a Twitter/X data export into a browsable,
searchable website — no server required.

## Background

Twitter/X lets you download a full archive of your account data:

More > Settings and privacy > Your account > Download an archive of your data

Once the archive is downloaded and extracted into this directory, `generate.py`
reads the data files and produces a self-contained static website in `output/`.

## Input files

The script reads the following files from the archive:

| File               | Contents                          |
| ------             | ----------                        |
| tweets.js          | All tweets, retweets, and replies |
| account.js         | Username and display name         |
| profile\_media/    | Profile avatar image              |
| longer\_tweets.txt | *(Optional)* Tab-delimited file mapping tweet URLs to longer body text, used to restore text that was truncated in the archive |

Other files present in a typical Twitter export (`like.js`, `profile.js`,
`personalization.js`, etc.) are not currently used.

## Setup

```
pip install jinja2
```

## Usage

```
python3 generate.py             # reads tweets.js (default)
python3 generate.py other.js    # reads a different tweets JS file
```

Then open `output/index.html` in a browser. Because the search feature uses
`fetch()`, you'll need a local web server to use it:

```
cd output && python3 -m http.server
```

## Output

```
output/
  index.html          # Page 1 of the tweet timeline
  page/               # Pages 2, 3, … of the timeline
  status/             # One file per tweet (individual tweet view)
  search.html         # Full-text search page
  search-index.json   # Pre-built search index loaded by search.html
  static/             # CSS and JavaScript
  tweets_media        # Symlink to tweets_media/ for local images and video
```

## Features

- **Paginated timeline** — tweets sorted newest-first, 20 per page
- **Individual tweet pages** — each tweet has its own URL under `status/`
- **Reply threading** — replies link to their parent tweet; replies to a tweet
  are listed below it on its status page
- **Media** — inline photos and videos served from local files when available,
  falling back to CDN URLs
- **Full-text search** — client-side, no server needed; loads a pre-built JSON
  index on first use
- **Keyboard navigation** — on both timeline and tweet pages:
  - Arrow keys
  - `h`/`l` or `k`/`j` (vim-style)
  - `a`/`d` or `w`/`s` (WASD gaming-style)
- **Swipe navigation** — swipe left/right on touch devices to move between
  pages or tweets

### Is it any good?

[Yes](https://news.ycombinator.com/item?id=3067434).

## License

Most of the code was written by an agentic AI. As such, it has no human author
and is not eligible for copyright protection.
