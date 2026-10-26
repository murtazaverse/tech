/* Progressive enhancements. Content, case studies, and planet links work without JS. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
  const motionButton = document.querySelector('.motion-toggle');
  let paused = false;
  try { paused = localStorage.getItem('murtazaverse-motion') === 'paused'; } catch (_) { /* Storage is optional. */ }

  function syncMotion() {
    const stopped = paused || reducedMotion.matches;
    root.dataset.motion = stopped ? 'paused' : 'running';
    if (motionButton) {
      motionButton.hidden = reducedMotion.matches;
      motionButton.setAttribute('aria-pressed', String(paused));
      motionButton.setAttribute('aria-label', paused ? 'Resume decorative motion' : 'Pause decorative motion');
      motionButton.querySelector('span').textContent = paused ? '▷' : 'Ⅱ';
    }
  }
  syncMotion();
  reducedMotion.addEventListener('change', syncMotion);
  motionButton?.addEventListener('click', () => {
    paused = !paused;
    try { localStorage.setItem('murtazaverse-motion', paused ? 'paused' : 'running'); } catch (_) { /* Storage is optional. */ }
    syncMotion();
  });
  function syncVisibility() { root.toggleAttribute('data-page-hidden', document.hidden); }
  document.addEventListener('visibilitychange', syncVisibility);
  syncVisibility();

  const menuButton = document.querySelector('.menu-toggle');
  const mobileNav = document.getElementById('mobile-nav');
  const mobileBreakpoint = matchMedia('(max-width: 950px)');
  function closeMenu(restoreFocus = false) {
    if (!menuButton || !mobileNav) return;
    mobileNav.hidden = true;
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open navigation');
    if (restoreFocus) menuButton.focus();
  }
  if (menuButton && mobileNav) {
    menuButton.hidden = false;
    menuButton.addEventListener('click', () => {
      const open = menuButton.getAttribute('aria-expanded') !== 'true';
      mobileNav.hidden = !open;
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    });
    mobileNav.addEventListener('click', event => {
      const link = event.target.closest('a');
      if (!link) return;
      closeMenu();
      const destination = new URL(link.href);
      if (destination.pathname === location.pathname && destination.hash) {
        const target = document.getElementById(destination.hash.slice(1));
        if (target) {
          target.setAttribute('tabindex', '-1');
          target.focus({ preventScroll: true });
        }
      }
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !mobileNav.hidden) closeMenu(true);
    });
    document.addEventListener('click', event => {
      if (!mobileNav.hidden && !event.target.closest('.site-header')) closeMenu();
    });
    mobileBreakpoint.addEventListener('change', () => closeMenu());
  }

  // No hiding of content unless IntersectionObserver is available.
  if ('IntersectionObserver' in window) {
    const sectionLinks = [...document.querySelectorAll('[data-section]')];
    const sections = [...document.querySelectorAll('main > section[id]')];
    const positions = new Map();
    const setActive = id => sectionLinks.forEach(link => {
      if (link.dataset.section === id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    const sectionObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => positions.set(entry.target.id, entry.isIntersecting));
      const visible = sections.find(section => positions.get(section.id) && section.id !== 'about');
      if (visible) setActive(visible.id);
    }, { rootMargin: '-15% 0px -50% 0px', threshold: 0 });
    sections.forEach(section => sectionObserver.observe(section));
    setActive(document.body.classList.contains('case-page') ? 'projects' : 'home');

    const reveals = document.querySelectorAll('.reveal');
    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.remove('is-waiting');
        revealObserver.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px 25px 0px', threshold: 0.05 });
    reveals.forEach(element => {
      if (!reducedMotion.matches && !paused) element.classList.add('is-waiting');
      revealObserver.observe(element);
    });
    root.classList.add('motion-ready');
    const solar = document.querySelector('.solar');
    if (solar) {
      const sceneObserver = new IntersectionObserver(entries => {
        solar.classList.toggle('is-offscreen', !entries[0].isIntersecting);
      }, { rootMargin: '50px' });
      sceneObserver.observe(solar);
    }
  }

  // One requestAnimationFrame per pointer update, scoped to the solar scene.
  const scene = document.querySelector('.solar-scene');
  if (scene) {
    let frame = 0;
    scene.addEventListener('pointermove', event => {
      if (!finePointer.matches || reducedMotion.matches || paused || frame) return;
      frame = requestAnimationFrame(() => {
        const bounds = scene.getBoundingClientRect();
        scene.style.setProperty('--pointer-x', `${event.clientX - bounds.left}px`);
        scene.style.setProperty('--pointer-y', `${event.clientY - bounds.top}px`);
        frame = 0;
      });
    }, { passive: true });
    scene.addEventListener('pointerleave', () => { if (frame) cancelAnimationFrame(frame); frame = 0; });
    window.addEventListener('pagehide', () => { if (frame) cancelAnimationFrame(frame); });
  }

  const description = document.getElementById('skill-description');
  const skillNodes = [...document.querySelectorAll('.constellation-node')];
  const skillConnections = [...document.querySelectorAll('.constellation-map line')];
  skillNodes.forEach(node => {
    node.setAttribute('aria-pressed', 'false');
    function select() {
      skillNodes.forEach(other => other.setAttribute('aria-pressed', String(other === node)));
      skillConnections.forEach(connection => {
        connection.classList.toggle('is-active', connection.dataset.from === node.dataset.node || connection.dataset.to === node.dataset.node);
      });
      if (description) description.textContent = `${node.dataset.skill} — ${node.dataset.description}`;
    }
    node.addEventListener('click', select);
    node.addEventListener('focus', select);
    node.addEventListener('pointerenter', () => { if (finePointer.matches) select(); });
  });

  // Close the mobile disclosure when traversing native browser history.
  window.addEventListener('hashchange', () => closeMenu());
})();
