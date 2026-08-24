/**
 * Murtaza Zaidi's Portfolio
 * Vanilla JS: theme toggle, mobile nav, scroll spy, project filters, hero typewriter.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------------------------------------------------- Theme ----- */
  var themeToggle = document.getElementById('theme-toggle');

  function currentTheme() {
    var explicit = root.getAttribute('data-theme');
    if (explicit) return explicit;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try {
        localStorage.setItem('theme', next);
      } catch (e) {}
    });
  }

  /* ----------------------------------------------------- Mobile nav ----- */
  var navToggle = document.getElementById('nav-toggle');
  var mobileNav = document.getElementById('mobile-nav');

  function closeNav() {
    if (!mobileNav) return;
    mobileNav.classList.remove('is-open');
    if (navToggle) navToggle.setAttribute('aria-expanded', 'false');
  }

  if (navToggle && mobileNav) {
    navToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = mobileNav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    mobileNav.addEventListener('click', function (e) {
      if (e.target.closest('a')) closeNav();
    });

    document.addEventListener('click', function (e) {
      if (!mobileNav.contains(e.target) && !navToggle.contains(e.target)) closeNav();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeNav();
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth > 900) closeNav();
    });
  }

  /* ------------------------------------------- Header shadow + spy ------ */
  var header = document.querySelector('.site-header');
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.nav a[href^="#"]'));
  var sections = navLinks
    .map(function (link) {
      return document.querySelector(link.getAttribute('href'));
    })
    .filter(Boolean);

  function onScroll() {
    if (header) header.classList.toggle('is-scrolled', window.scrollY > 8);

    var offset = (header ? header.offsetHeight : 0) + 90;
    var activeId = null;

    sections.forEach(function (section) {
      if (section.getBoundingClientRect().top <= offset) activeId = section.id;
    });

    // Highlight the last section once the page is scrolled to the bottom.
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 4 && sections.length) {
      activeId = sections[sections.length - 1].id;
    }

    navLinks.forEach(function (link) {
      link.classList.toggle('is-active', link.getAttribute('href') === '#' + activeId);
    });
  }

  var ticking = false;
  window.addEventListener(
    'scroll',
    function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        onScroll();
        ticking = false;
      });
    },
    { passive: true }
  );
  onScroll();

  /* ------------------------------------------------ Project filters ----- */
  var filterButtons = Array.prototype.slice.call(document.querySelectorAll('.filters button'));
  var projectCards = Array.prototype.slice.call(document.querySelectorAll('.project-card'));

  filterButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var filter = button.getAttribute('data-filter');

      filterButtons.forEach(function (other) {
        other.classList.toggle('is-active', other === button);
      });

      projectCards.forEach(function (card) {
        card.hidden = filter !== 'all' && card.getAttribute('data-cat') !== filter;
      });
    });
  });

  /* --------------------------------------------------- Typewriter ------- */
  var typingEl = document.querySelector('.typing');

  if (typingEl) {
    var strings = [];
    try {
      strings = JSON.parse(typingEl.getAttribute('data-strings') || '[]');
    } catch (e) {
      strings = [];
    }

    if (strings.length && prefersReducedMotion) {
      typingEl.textContent = strings[0];
    } else if (strings.length) {
      var stringIndex = 0;
      var charIndex = 0;
      var deleting = false;

      var step = function () {
        var full = strings[stringIndex];
        charIndex += deleting ? -1 : 1;
        typingEl.textContent = full.slice(0, charIndex);

        var delay = deleting ? 28 : 62;

        if (!deleting && charIndex === full.length) {
          deleting = true;
          delay = 1600;
        } else if (deleting && charIndex === 0) {
          deleting = false;
          stringIndex = (stringIndex + 1) % strings.length;
          delay = 320;
        }

        window.setTimeout(step, delay);
      };

      window.setTimeout(step, 600);
    }
  }

  /* --------------------------------------------------------- Misc ------- */
  var year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();
