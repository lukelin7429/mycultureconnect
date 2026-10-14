/* ============================================================
   Fit each slide's text to its frame.
   ------------------------------------------------------------
   Every size in deck.css is a fixed px value, tuned so the FULLEST slide of a
   type still fits the 1200x675 canvas. A slide with less on it therefore sat
   small in a half-empty frame, and teachers at the back of the room could not
   read it. Enlarging the fixed sizes a notch never fixed that — the notch had
   to stay small enough for the fullest slide.

   So the slide measures itself instead: its content is zoomed (CSS zoom on the
   slide's direct children, driven by --k) to the largest factor that still
   fits, checked with every hidden answer shown and hidden, so nothing jumps or
   clips when an answer is revealed. Used by the live deck (deck.js) and by the
   PDF/PPTX export (export_decks.py), so all three look the same.
   ============================================================ */
(function () {
  var MIN = 0.7, MAX = 2.2;
  /* layouts where growing forever would not "overflow", it would just swallow
     the picture or the video — so they get a ceiling of their own */
  /* a photo may give up to a third of the slide to its caption; the world map is limited by its labels instead (placePicture) */
  var CAP = { 'hs-map--photo': 1.3, 'hs-map': 1.5, 'hs-video': 1.5, 'hs-title': 1.8, 'hs-closing': 1.6, 'hs-bigstat': 1.6 };
  var CAP_ORDER = ['hs-map--photo', 'hs-map', 'hs-video', 'hs-title', 'hs-closing', 'hs-bigstat'];
  var REVEAL = '[data-reveal-group], .hs-tf, .hs-hintbtn, .hs-sortitem';
  var SKIP = '.hs-art, .hs-mapimg, .hs-school';

  function kind(hs) {
    for (var i = 0; i < CAP_ORDER.length; i++) if (hs.classList.contains(CAP_ORDER[i])) return CAP_ORDER[i];
    return '';
  }

  /* A picture slide: the caption has its own row, the picture fills what is left
     above it. When part of the picture must stay visible (data-keep: the map's
     pins and labels), slide the picture so that part sits between the heading
     and the caption — and report "does not fit" when there is no room for it. */
  function placePicture(hs) {
    var keep = hs.getAttribute('data-keep');
    var box = hs.querySelector('.hs-mapimg'), img = box && box.querySelector('img');
    if (!keep || !img) return true;
    var f = keep.split(','), top = +f[0], bottom = +f[1];
    var B = box.clientHeight, W = box.clientWidth;
    var ratio = (img.naturalWidth && img.naturalHeight) ? img.naturalHeight / img.naturalWidth : 9 / 16;
    var I = Math.max(B, W * ratio);                       /* the picture's drawn height (cover) */
    var head = hs.querySelector('.hs-head');
    var scale = hs.getBoundingClientRect().width / hs.offsetWidth || 1;
    var free = head ? (head.getBoundingClientRect().bottom - hs.getBoundingClientRect().top) / scale + 8 : 0;
    var need = (bottom - top) * I;
    if (I <= B) { box.style.setProperty('--map-y', '50%'); return need <= B - free; }
    var want = (free + B) / 2 - (top + bottom) / 2 * I;   /* the picture's offset that centers the band */
    var y = Math.min(0, Math.max(B - I, want));
    box.style.setProperty('--map-y', (y / (B - I) * 100).toFixed(1) + '%');
    return need <= B - free && top * I + y >= free - 1 && bottom * I + y <= B + 1;
  }

  function clipped(hs) {
    if (!placePicture(hs)) return true;
    if (hs.scrollHeight > hs.clientHeight + 1 || hs.scrollWidth > hs.clientWidth + 1) return true;
    var cs = getComputedStyle(hs), box = hs.getBoundingClientRect();
    var scale = box.width / hs.offsetWidth || 1;                 // the canvas is itself scaled to the stage
    var bottom = box.bottom - parseFloat(cs.paddingBottom) * scale + 1;
    var right = box.right - parseFloat(cs.paddingRight) * scale + 1;
    var kids = [];
    for (var i = 0; i < hs.children.length; i++) {
      var c = hs.children[i];
      if (c.matches(SKIP) || getComputedStyle(c).display === 'none') continue;
      kids.push(c.getBoundingClientRect());
    }
    for (var a = 0; a < kids.length; a++) {
      if (kids[a].bottom > bottom || kids[a].right > right) return true;
      for (var b = a + 1; b < kids.length; b++) {
        /* overlay layouts (map, photo) never overflow: their boxes collide instead */
        if (kids[a].bottom > kids[b].top + 1 && kids[b].bottom > kids[a].top + 1 &&
            kids[a].right > kids[b].left + 1 && kids[b].right > kids[a].left + 1) return true;
      }
    }
    return false;
  }

  /* Both states must fit: answers hidden (the tap hint is showing) and answers
     shown (the explanation is showing). The export prints a slide twice, once
     in each state — testing both here gives the two pages the same size. */
  function fitsAt(hs, k, answers) {
    hs.style.setProperty('--k', k);
    if (!answers.length) return !clipped(hs);
    var was = answers.map(function (el) { return el.classList.contains('is-revealed'); });
    answers.forEach(function (el) { el.classList.add('is-revealed'); });
    var bad = clipped(hs);
    if (!bad) {
      answers.forEach(function (el) { el.classList.remove('is-revealed'); });
      bad = clipped(hs);
    }
    answers.forEach(function (el, i) { el.classList.toggle('is-revealed', was[i]); });
    return !bad;
  }

  function fitOne(hs) {
    var hidden = [].slice.call(hs.querySelectorAll(REVEAL));
    if (hs.matches('[data-reveal-group]')) hidden.push(hs);

    var lo = MIN, hi = CAP[kind(hs)] || MAX, k;
    if (fitsAt(hs, hi, hidden)) k = hi;
    else if (!fitsAt(hs, lo, hidden)) k = lo;
    else {
      for (var i = 0; i < 9; i++) {
        var mid = (lo + hi) / 2;
        if (fitsAt(hs, mid, hidden)) lo = mid; else hi = mid;
      }
      /* Stop a little short of the edge. A second layout pass can wrap one line
         differently, and a slide fitted to the last pixel then overflows by a few. */
      k = Math.floor(lo * 0.97 * 100) / 100;
    }
    hs.style.setProperty('--k', k);
    hs.setAttribute('data-k', k);
  }

  window.hsFit = function (root) {
    root = root || document;
    var host = root.documentElement || root;
    host.classList.add('hs-fitting');           /* entrance transforms would skew the measurement */
    [].forEach.call(root.querySelectorAll('.hs'), fitOne);
    host.classList.remove('hs-fitting');
  };
})();
