/* Site-wide search (client-side, zero dependency, house style).
   Self-mounts a button into .site-header (before .nav-toggle), so pages only
   need this script + search.css + /search.json — no markup changes. */
(function () {
  var LABEL = 'Search';
  var PLACEHOLDER = 'Search My Culture Connect…';
  var EMPTY = 'No matches — try another word.';

  var btn = document.getElementById('siteSearchBtn');
  if (!btn) {
    var host = document.querySelector('.site-header .wrap') ||
               document.querySelector('.site-header') ||
               document.querySelector('header');
    if (host) {
      btn = document.createElement('button');
      btn.id = 'siteSearchBtn';
      btn.type = 'button';
      btn.className = 'nav-search-btn';
      btn.setAttribute('aria-label', 'Search this site');
      btn.innerHTML = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg><span class="nav-search-label">' + LABEL + '</span><kbd>/</kbd>';
      var tog = host.querySelector('.nav-toggle');
      if (tog && tog.parentNode) tog.parentNode.insertBefore(btn, tog);
      else host.appendChild(btn);
    }
  }
  if (!btn) return;

  var index = null, overlay = null, input = null, list = null, emptyEl = null;
  var rows = [], active = -1, loading = false;

  function sectionOf(url) {
    var seg = (url || '').split('/').filter(Boolean)[0] || '';
    if (!seg) return 'Home';
    return seg.replace(/[-_]/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function load() {
    if (index || loading) return;
    loading = true;
    fetch('/search.json', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        index = data.map(function (it) {
          var t = it.title || '', b = it.body || '';
          return { title: t, url: it.url, body: b, section: sectionOf(it.url),
                   hay: (t + ' ' + b).toLowerCase() };
        });
        loading = false;
      })
      .catch(function () { loading = false; });
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function highlight(text, words) {
    var out = esc(text);
    words.forEach(function (w) { if (!w) return; var re = new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig'); out = out.replace(re, '<mark>$1</mark>'); });
    return out;
  }
  function snippet(body, words) {
    var lc = body.toLowerCase(), pos = -1;
    for (var i = 0; i < words.length; i++) { var p = lc.indexOf(words[i]); if (p !== -1 && (pos === -1 || p < pos)) pos = p; }
    if (pos > 60) body = '…' + body.slice(pos - 50);
    return body.length > 160 ? body.slice(0, 160) + '…' : body;
  }
  function search(q) {
    q = q.trim().toLowerCase(); if (!q) return [];
    var words = q.split(/\s+/), res = [];
    index.forEach(function (it) {
      var ok = true, score = 0;
      for (var i = 0; i < words.length; i++) {
        var w = words[i];
        if (it.hay.indexOf(w) === -1) { ok = false; break; }
        if (it.title.toLowerCase().indexOf(w) !== -1) score += 12;
        score += 1;
      }
      if (ok) res.push({ it: it, score: score });
    });
    res.sort(function (a, b) { return b.score - a.score; });
    return res.slice(0, 14).map(function (r) { return r.it; });
  }
  function render(q) {
    var results = q.trim() ? search(q) : [];
    var words = q.trim().toLowerCase().split(/\s+/);
    rows = results; active = results.length ? 0 : -1;
    if (!q.trim()) { list.innerHTML = ''; emptyEl.hidden = true; return; }
    if (!results.length) { list.innerHTML = ''; emptyEl.hidden = false; return; }
    emptyEl.hidden = true;
    list.innerHTML = results.map(function (it, i) {
      return '<li class="rs-item' + (i === 0 ? ' is-active' : '') + '" role="option" data-url="' + esc(it.url) + '">' +
        '<a href="' + esc(it.url) + '" tabindex="-1">' +
        '<span class="rs-sec">' + esc(it.section) + '</span>' +
        '<span class="rs-title">' + highlight(it.title, words) + '</span>' +
        (it.body ? '<span class="rs-snippet">' + highlight(snippet(it.body, words), words) + '</span>' : '') +
        '</a></li>';
    }).join('');
    Array.prototype.forEach.call(list.children, function (li, i) { li.addEventListener('mousemove', function () { setActive(i); }); });
  }
  function setActive(i) {
    if (i < 0 || i >= rows.length) return; active = i;
    Array.prototype.forEach.call(list.children, function (li, j) { li.classList.toggle('is-active', j === i); });
    var el = list.children[i]; if (el) el.scrollIntoView({ block: 'nearest' });
  }
  function go(i) { if (i >= 0 && i < rows.length) window.location.href = rows[i].url; }
  function onKey(e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(Math.min(active + 1, rows.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(Math.max(active - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); go(active < 0 ? 0 : active); }
    else if (e.key === 'Escape') { e.preventDefault(); close(); }
  }
  function build() {
    overlay = document.createElement('div');
    overlay.className = 'rs-overlay';
    overlay.innerHTML =
      '<div class="rs-modal" role="dialog" aria-modal="true" aria-label="Search this site">' +
        '<div class="rs-bar">' +
          '<svg class="rs-mag" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>' +
          '<input type="search" class="rs-input" placeholder="' + PLACEHOLDER + '" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Search query">' +
          '<kbd class="rs-esc">esc</kbd>' +
        '</div>' +
        '<ul class="rs-results" role="listbox"></ul>' +
        '<div class="rs-empty" hidden>' + EMPTY + '</div>' +
        '<div class="rs-foot"><span><kbd>↑</kbd><kbd>↓</kbd></span><span><kbd>↵</kbd></span><span><kbd>esc</kbd></span></div>' +
      '</div>';
    document.body.appendChild(overlay);
    input = overlay.querySelector('.rs-input');
    list = overlay.querySelector('.rs-results');
    emptyEl = overlay.querySelector('.rs-empty');
    overlay.addEventListener('mousedown', function (e) { if (e.target === overlay) close(); });
    overlay.querySelector('.rs-esc').addEventListener('click', close);
    input.addEventListener('input', function () { render(input.value); });
    input.addEventListener('keydown', onKey);
    list.addEventListener('mousedown', function (e) { var li = e.target.closest('.rs-item'); if (li) { e.preventDefault(); window.location.href = li.getAttribute('data-url'); } });
  }
  function open() {
    if (!overlay) build();
    load();
    document.documentElement.classList.add('rs-open');
    overlay.classList.add('is-open');
    input.value = ''; render('');
    setTimeout(function () { input.focus(); }, 20);
  }
  function close() { if (overlay) { overlay.classList.remove('is-open'); document.documentElement.classList.remove('rs-open'); } }

  btn.addEventListener('click', open);
  document.addEventListener('keydown', function (e) {
    var isOpen = overlay && overlay.classList.contains('is-open');
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
    if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) { e.preventDefault(); isOpen ? close() : open(); }
    else if (e.key === '/' && !isOpen && !typing) { e.preventDefault(); open(); }
  });
})();
