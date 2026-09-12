/* ============================================================
   Reusable full-page slide-deck viewer · swipe right/left = prev/next
   ------------------------------------------------------------
   Markup (rendered per deck by build.py):
   <div class="deck" data-index="0">
     <div class="deck-stage">
       <div class="deck-track">
         <div class="deck-slide"><img src="01.jpg" alt="Slide 1"></div>
         <div class="deck-slide"><img src="02.jpg" alt="Slide 2"></div>
         ...
       </div>
       <button class="deck-arrow prev" aria-label="Previous slide">&#8249;</button>
       <button class="deck-arrow next" aria-label="Next slide">&#8250;</button>
     </div>
     <div class="deck-progress"><div class="bar"></div></div>
   </div>
   Reusable for any future school visit deck — just point build.py at a new
   folder of NN.jpg slide images and this script drives navigation.
   ============================================================ */
(function () {
  function initDeck(deck) {
    var track = deck.querySelector('.deck-track');
    var slides = Array.prototype.slice.call(deck.querySelectorAll('.deck-slide'));
    var n = slides.length;
    if (!n) return;
    var posEl = deck.querySelector('.deck-pos');
    var bar = deck.querySelector('.deck-progress .bar');
    var i = 0;

    function go(target) {
      i = Math.max(0, Math.min(n - 1, target));
      track.style.transform = 'translateX(' + (-i * 100) + '%)';
      if (posEl) posEl.textContent = (i + 1);
      if (bar) bar.style.width = ((i + 1) / n * 100) + '%';
      slides.forEach(function (s, idx) { s.setAttribute('aria-hidden', idx === i ? 'false' : 'true'); });
    }
    function next() { go(i + 1); }
    function prev() { go(i - 1); }

    var nx = deck.querySelector('.deck-arrow.next');
    var pv = deck.querySelector('.deck-arrow.prev');
    if (nx) nx.addEventListener('click', next);
    if (pv) pv.addEventListener('click', prev);

    // click zones on the stage itself (left third = prev, right third = next)
    var stage = deck.querySelector('.deck-stage');
    stage.addEventListener('click', function (e) {
      if (e.target.closest('.deck-arrow')) return;
      // HTML slides carry their own controls (quiz options, reveal buttons, the
      // video facade) — a tap on those must not also flip the slide.
      if (e.target.closest('.hs-opt, .hs-tf, .hs-revealbtn, .hs-yt')) return;
      var r = stage.getBoundingClientRect();
      var x = e.clientX - r.left;
      if (x < r.width * 0.32) prev();
      else if (x > r.width * 0.68) next();
    });

    // keyboard
    document.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === ' ') { next(); }
      else if (e.key === 'ArrowLeft') { prev(); }
    });

    // touch / pointer swipe
    var startX = null, startY = null, dragging = false;
    var THRESH = 40;
    stage.addEventListener('touchstart', function (e) {
      var t = e.touches[0];
      startX = t.clientX; startY = t.clientY; dragging = true;
    }, { passive: true });
    stage.addEventListener('touchmove', function (e) {
      if (!dragging) return;
    }, { passive: true });
    stage.addEventListener('touchend', function (e) {
      if (!dragging || startX === null) return;
      dragging = false;
      var t = e.changedTouches[0];
      var dx = t.clientX - startX;
      var dy = t.clientY - startY;
      if (Math.abs(dx) > THRESH && Math.abs(dx) > Math.abs(dy)) {
        // swipe right (finger moves right, dx > 0) = next slide, per spec
        if (dx > 0) next(); else prev();
      }
      startX = null;
    });

    // mouse drag (desktop testing / trackpad)
    var mDown = false, mStartX = 0;
    stage.addEventListener('mousedown', function (e) { mDown = true; mStartX = e.clientX; });
    window.addEventListener('mouseup', function (e) {
      if (!mDown) return;
      mDown = false;
      var dx = e.clientX - mStartX;
      if (Math.abs(dx) > THRESH) { if (dx > 0) next(); else prev(); }
    });

    // ---- HTML slides: scale the fixed 1200x675 canvas to fit the stage ----
    var canvases = Array.prototype.slice.call(deck.querySelectorAll('.hs-canvas'));
    function rescale() {
      if (!canvases.length) return;
      var w = deck.querySelector('.deck-stage').clientWidth;
      var s = w / 1200;
      canvases.forEach(function (c) { c.style.setProperty('--hs-scale', s); });
    }
    if (canvases.length) {
      rescale();
      window.addEventListener('resize', rescale);
      if (window.ResizeObserver) new ResizeObserver(rescale).observe(deck.querySelector('.deck-stage'));
    }

    // ---- click-to-reveal: quiz options, true/false rows, reveal buttons ----
    deck.addEventListener('click', function (e) {
      var opt = e.target.closest('.hs-opt, .hs-revealbtn');
      if (opt) {
        var group = opt.closest('[data-reveal-group]');
        if (group) group.classList.add('is-revealed');
        return;
      }
      var tf = e.target.closest('.hs-tf');
      if (tf) { tf.classList.toggle('is-revealed'); return; }
      var yt = e.target.closest('.hs-yt');
      if (yt && !yt.querySelector('iframe')) {
        var f = document.createElement('iframe');
        f.src = 'https://www.youtube-nocookie.com/embed/' + yt.dataset.yt + '?autoplay=1&rel=0';
        f.allow = 'autoplay; encrypted-media; fullscreen';
        f.setAttribute('allowfullscreen', '');
        yt.innerHTML = '';
        yt.appendChild(f);
      }
    });

    go(0);
  }

  document.addEventListener('DOMContentLoaded', function () {
    Array.prototype.slice.call(document.querySelectorAll('.deck')).forEach(initDeck);
  });
})();
