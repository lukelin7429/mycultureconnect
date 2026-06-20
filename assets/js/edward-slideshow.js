/* ============================================================
   Edward Huang section · reusable photo slideshow
   ------------------------------------------------------------
   Markup:
   <div class="eshow" data-interval="5000">
     <div class="eshow-track">
       <figure class="eshow-slide"><img ...><figcaption>...</figcaption></figure>
       ...
     </div>
     <button class="eshow-arrow prev">‹</button>
     <button class="eshow-arrow next">›</button>
     <div class="eshow-dots"></div>
   </div>
   Auto-advances; pauses on hover/focus; respects prefers-reduced-motion;
   keyboard arrows when focused. Each .eshow is independent.
   ============================================================ */
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function initShow(show) {
    var track = show.querySelector('.eshow-track');
    var slides = Array.prototype.slice.call(show.querySelectorAll('.eshow-slide'));
    if (slides.length < 2) return;
    var dotsWrap = show.querySelector('.eshow-dots');
    var interval = parseInt(show.getAttribute('data-interval'), 10) || 5000;
    var i = 0, timer = null;

    // build dots
    var dots = [];
    if (dotsWrap) {
      slides.forEach(function (_, idx) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'eshow-dot';
        b.setAttribute('aria-label', 'Slide ' + (idx + 1));
        b.addEventListener('click', function () { go(idx); restart(); });
        dotsWrap.appendChild(b);
        dots.push(b);
      });
    }

    function go(n) {
      i = (n + slides.length) % slides.length;
      track.style.transform = 'translateX(' + (-i * 100) + '%)';
      slides.forEach(function (s, idx) { s.setAttribute('aria-hidden', idx === i ? 'false' : 'true'); });
      dots.forEach(function (d, idx) { d.classList.toggle('on', idx === i); });
    }
    function next() { go(i + 1); }
    function prev() { go(i - 1); }
    function start() { if (!reduce) timer = setInterval(next, interval); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function restart() { stop(); start(); }

    var nx = show.querySelector('.eshow-arrow.next');
    var pv = show.querySelector('.eshow-arrow.prev');
    if (nx) nx.addEventListener('click', function () { next(); restart(); });
    if (pv) pv.addEventListener('click', function () { prev(); restart(); });

    show.addEventListener('mouseenter', stop);
    show.addEventListener('mouseleave', start);
    show.addEventListener('focusin', stop);
    show.addEventListener('focusout', start);
    show.setAttribute('tabindex', '0');
    show.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { next(); restart(); }
      else if (e.key === 'ArrowLeft') { prev(); restart(); }
    });

    go(0);
    start();
  }

  document.addEventListener('DOMContentLoaded', function () {
    Array.prototype.slice.call(document.querySelectorAll('.eshow')).forEach(initShow);
  });
})();
