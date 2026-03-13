/* Client-side search for Twitter archive */
(function () {
  'use strict';

  let allTweets = [];
  let loaded = false;

  const input = document.getElementById('search-input');
  const status = document.getElementById('search-status');
  const results = document.getElementById('search-results');

  if (!input) return;

  // Determine path to search-index.json relative to current page
  const indexPath = document.documentElement.dataset.root + 'search-index.json';

  function loadIndex() {
    status.textContent = 'Loading…';
    fetch(indexPath)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        allTweets = data;
        loaded = true;
        status.textContent = allTweets.length + ' tweets indexed. Start typing to search.';
      })
      .catch(function () {
        status.textContent = 'Could not load search index.';
      });
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function highlight(text, query) {
    if (!query) return escapeHtml(text);
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp('(' + escaped + ')', 'gi');
    return escapeHtml(text).replace(re, '<mark>$1</mark>');
  }

  function renderTweet(tweet, query) {
    const tweetPath = document.documentElement.dataset.root + 'status/' + tweet.id;
    const rtClass = tweet.is_rt ? ' is-rt' : '';
    const rtLabel = tweet.is_rt
      ? '<span class="rt-label">&#x1F501; Retweet</span>'
      : '';
    const mediaIcon = tweet.has_media ? ' &#x1F4F7;' : '';
    const bodyHtml = highlight(tweet.text, query);
    return (
      '<div class="tweet-card' + rtClass + '">' +
        '<div class="tweet-meta">' +
          rtLabel +
          '<span class="tweet-date"><a href="' + tweetPath + '">' + escapeHtml(tweet.date) + '</a></span>' +
          mediaIcon +
        '</div>' +
        '<div class="tweet-body">' + bodyHtml + '</div>' +
      '</div>'
    );
  }

  function doSearch(query) {
    if (!loaded) return;
    const q = query.trim().toLowerCase();
    if (!q) {
      results.innerHTML = '';
      status.textContent = allTweets.length + ' tweets indexed. Start typing to search.';
      return;
    }
    const matches = allTweets.filter(function (t) {
      return t.text.toLowerCase().includes(q);
    });
    status.textContent = matches.length + ' result' + (matches.length !== 1 ? 's' : '') + ' for "' + escapeHtml(query) + '"';
    if (matches.length === 0) {
      results.innerHTML = '<p class="empty-state">No tweets matched your search.</p>';
      return;
    }
    const top = matches.slice(0, 50);
    results.innerHTML = top.map(function (t) { return renderTweet(t, query); }).join('');
    if (matches.length > 50) {
      results.innerHTML += '<p class="empty-state">Showing first 50 of ' + matches.length + ' results.</p>';
    }
  }

  // Debounce
  let timer;
  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { doSearch(input.value); }, 200);
  });

  // Load index immediately (small file, cache-friendly)
  loadIndex();
}());
