/* My Culture Connect — interactions */
(function () {
  // ----- mobile nav -----
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('nav.main');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      nav.classList.toggle('open');
    });
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { nav.classList.remove('open'); });
    });
  }

  // ----- slideshow -----
  document.querySelectorAll('.slideshow').forEach(function (box) {
    var slides = Array.prototype.slice.call(box.querySelectorAll('.slide'));
    if (!slides.length) return;
    var navWrap = box.querySelector('.slidenav');
    var i = 0, timer;
    slides.forEach(function (s, idx) {
      var dot = document.createElement('button');
      dot.setAttribute('aria-label', 'Slide ' + (idx + 1));
      dot.addEventListener('click', function () { go(idx); reset(); });
      navWrap.appendChild(dot);
    });
    var dots = Array.prototype.slice.call(navWrap.children);
    function go(n) {
      slides[i].classList.remove('on'); dots[i].classList.remove('on');
      i = (n + slides.length) % slides.length;
      slides[i].classList.add('on'); dots[i].classList.add('on');
    }
    function reset() { clearInterval(timer); timer = setInterval(function () { go(i + 1); }, 5000); }
    var prev = box.querySelector('.slidearrow.prev');
    var next = box.querySelector('.slidearrow.next');
    if (prev) prev.addEventListener('click', function () { go(i - 1); reset(); });
    if (next) next.addEventListener('click', function () { go(i + 1); reset(); });
    go(0); reset();
  });

  // ----- count-up animation -----
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var suffix = el.getAttribute('data-suffix') || '';
    var dur = 1500, start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      el.textContent = Math.round(target * eased).toLocaleString('en-US') + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ----- staggered reveal on scroll -----
  // assign stagger index within each parent group
  var groups = {};
  document.querySelectorAll('[data-reveal]').forEach(function (el) {
    var key = el.parentNode;
    groups.i = groups.i || new Map();
    var n = groups.i.get(key) || 0;
    el.style.setProperty('--d', n);
    groups.i.set(key, n + 1);
  });

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        var c = e.target.querySelector('[data-count]');
        if (c && !c.dataset.done) { c.dataset.done = '1'; countUp(c); }
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.18 });
  document.querySelectorAll('[data-reveal]').forEach(function (el) { io.observe(el); });

  // ----- contact form (mailto fallback; swap to Apps Script later) -----
  var cf = document.getElementById('contactForm');
  if (cf) {
    cf.addEventListener('submit', function (e) {
      e.preventDefault();
      var get = function (n) { var el = cf.elements[n]; return el ? el.value.trim() : ''; };
      var subject = 'Website inquiry — ' + (get('interest') || 'General') + ' (' + (get('name') || 'no name') + ')';
      var body =
        'Name: ' + get('name') + '\n' +
        'Email: ' + get('email') + '\n' +
        'From (City, State, Country): ' + get('location') + '\n' +
        'Interested in: ' + get('interest') + '\n\n' +
        'Message:\n' + get('message') + '\n';
      window.location.href = 'mailto:luke@mycultureconnect.org?subject=' +
        encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
    });
  }

  // ----- footer year -----
  var yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();
})();
