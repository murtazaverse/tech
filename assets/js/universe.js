/* Progressive enhancements. Content, case studies, and planet links work without JS. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const motionButton = document.querySelector('.motion-toggle');
  let paused = false;
  let syncOrbit = () => {};
  let syncSpaceTravel = () => {};
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
    syncOrbit();
    syncSpaceTravel();
  }
  syncMotion();
  reducedMotion.addEventListener('change', syncMotion);
  motionButton?.addEventListener('click', () => {
    paused = !paused;
    try { localStorage.setItem('murtazaverse-motion', paused ? 'paused' : 'running'); } catch (_) { /* Storage is optional. */ }
    syncMotion();
  });
  function syncVisibility() {
    root.toggleAttribute('data-page-hidden', document.hidden);
    syncOrbit();
    syncSpaceTravel();
  }
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

  // Native anchors land on visible section content, below the actual header.
  // Track the last heading to cross that same line, rather than the first of
  // two overlapping sections inside a viewport-dependent observer band.
  const sectionLinks = [...document.querySelectorAll('[data-section]')];
  const navigationIds = new Set(sectionLinks.map(link => link.dataset.section));
  const navigationSections = [...document.querySelectorAll('main > section[id]')]
    .filter(section => navigationIds.has(section.id))
    .map(section => ({ id: section.id, marker: section.querySelector('.section-index') || section }));
  let navigationOffset = 112;
  let navigationFrame = 0;
  let activeSection = '';
  function setActiveSection(id) {
    if (id === activeSection) return;
    activeSection = id;
    sectionLinks.forEach(link => {
      if (link.dataset.section === id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  function updateNavigation() {
    navigationFrame = 0;
    syncSpaceTravel();
    if (!navigationSections.length) {
      setActiveSection(document.body.classList.contains('case-page') ? 'projects' : 'home');
      return;
    }
    let id = 'home';
    for (const section of navigationSections) {
      if (section.marker.getBoundingClientRect().top <= navigationOffset + 2) id = section.id;
    }
    if (scrollY > 0 && scrollY + innerHeight >= document.documentElement.scrollHeight - 2) {
      id = navigationSections[navigationSections.length - 1].id;
    }
    setActiveSection(id);
  }
  function scheduleNavigation() {
    if (!navigationFrame) navigationFrame = requestAnimationFrame(updateNavigation);
  }
  function measureNavigation() {
    const header = document.querySelector('.site-header');
    const inner = header?.querySelector('.header-inner');
    if (inner) {
      const border = parseFloat(getComputedStyle(header).borderBottomWidth) || 0;
      navigationOffset = Math.ceil(inner.getBoundingClientRect().height + border) + 24;
      root.style.setProperty('--navigation-offset', `${navigationOffset}px`);
    }
    scheduleNavigation();
  }
  const headerInner = document.querySelector('.header-inner');
  if (headerInner && 'ResizeObserver' in window) new ResizeObserver(measureNavigation).observe(headerInner);
  window.addEventListener('scroll', scheduleNavigation, { passive: true });
  window.addEventListener('resize', measureNavigation, { passive: true });
  window.addEventListener('hashchange', scheduleNavigation);
  window.addEventListener('pageshow', measureNavigation);
  document.fonts.ready.then(measureNavigation);
  measureNavigation();
  updateNavigation();

  // Scroll reveals four quiet encounters at different depths. Text stays in
  // normal flow; the background shares the existing scroll animation frame.
  const universe = document.querySelector('.cosmic-background');
  if (universe) {
    const encounters = [
      {node:universe.querySelector('[data-world=saturn]'),start:.035,end:.34,strength:.36,mobileStrength:.23},
      {node:universe.querySelector('[data-world=earth]'),start:.30,end:.57,strength:.19,mobileStrength:.13},
      {node:universe.querySelector('[data-world=mars]'),start:.52,end:.74,strength:.30,mobileStrength:.21},
      {node:universe.querySelector('[data-world=pluto]'),start:.68,end:1,strength:.30,mobileStrength:.20}
    ];
    const clamp = value => Math.max(0,Math.min(1,value));
    const smooth = value => { const x = clamp(value); return x*x*(3-2*x); };
    syncSpaceTravel = () => {
      if (document.hidden || paused) return;
      const progress = clamp(scrollY / Math.max(1,root.scrollHeight-innerHeight));
      const still = reducedMotion.matches;
      const travel = still ? 0 : progress * innerHeight;
      universe.style.setProperty('--galaxy-y', `${-travel*.20}px`);
      universe.style.setProperty('--galaxy-scale', String(still ? 1 : 1+progress*.055));
      universe.style.setProperty('--stars-near-y', `${-travel*.30}px`);
      universe.style.setProperty('--stars-far-y', `${-travel*.11}px`);
      universe.style.setProperty('--debris-y', `${-travel*.08}px`);
      encounters.forEach(({node,start,end,strength,mobileStrength}) => {
        if (!node) return;
        const phase = (progress-start)/(end-start);
        const inside = phase>0 && phase<1;
        const visibility = still ? Number(inside) : smooth(phase/.18)*(1-smooth((phase-.72)/.28));
        node.style.opacity = String(visibility*(innerWidth<=760 ? mobileStrength : strength));
        const center = still ? .55 : 1.05-clamp(phase)*1.2;
        node.style.setProperty('--encounter-y', `${center*innerHeight}px`);
      });
    };
    syncSpaceTravel();
  }

  // No hiding of content unless IntersectionObserver is available.
  if ('IntersectionObserver' in window) {
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
    const illustrations = document.querySelectorAll('[data-illustration]');
    const illustrationObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => entry.target.classList.toggle('is-offscreen', !entry.isIntersecting));
    }, { rootMargin: '80px' });
    illustrations.forEach(illustration => illustrationObserver.observe(illustration));
    const solar = document.querySelector('.solar');
    if (solar) {
      const sceneObserver = new IntersectionObserver(entries => {
        solar.classList.toggle('is-offscreen', !entries[0].isIntersecting);
        syncOrbit();
      }, { rootMargin: '50px' });
      sceneObserver.observe(solar);
    }
  }

  // One composited light follows viewport coordinates on every portfolio page.
  // Pointer type keeps touch input free of cursor decoration, including hybrids.
  const cursorGlow = document.querySelector('.cursor-glow');
  if (cursorGlow) {
    let glowFrame = 0;
    let cursorX = 0;
    let cursorY = 0;
    const hideGlow = () => {
      cancelAnimationFrame(glowFrame);
      glowFrame = 0;
      cursorGlow.removeAttribute('data-active');
    };
    document.addEventListener('pointermove', event => {
      if (event.pointerType !== 'mouse' || reducedMotion.matches || paused || document.hidden) {
        hideGlow();
        return;
      }
      cursorX = event.clientX;
      cursorY = event.clientY;
      if (glowFrame) return;
      glowFrame = requestAnimationFrame(() => {
        glowFrame = 0;
        if (reducedMotion.matches || paused || document.hidden) return;
        cursorGlow.style.transform = `translate3d(${cursorX}px, ${cursorY}px, 0)`;
        cursorGlow.setAttribute('data-active', '');
      });
    }, { passive: true });
    document.addEventListener('pointerdown', event => {
      if (event.pointerType !== 'mouse') hideGlow();
    }, { passive: true });
    document.addEventListener('pointerleave', hideGlow);
    document.addEventListener('visibilitychange', () => { if (document.hidden) hideGlow(); });
    window.addEventListener('blur', hideGlow);
    window.addEventListener('pagehide', hideGlow);
    reducedMotion.addEventListener('change', hideGlow);
    motionButton?.addEventListener('click', hideGlow);
  }

  // Orbital navigation pauses locally; the ambient cursor light stays page-wide.
  const scene = document.querySelector('.solar-scene');
  if (scene) {
    const solar = scene.closest('.solar');
    const tilt = -28 * Math.PI / 180;
    const planets = [...scene.querySelectorAll('[data-orbit-radius]')].map(element => ({
      element,
      radius: Number(element.dataset.orbitRadius),
      phase: Number(element.dataset.orbitPhase) * Math.PI / 180,
      startX: parseFloat(element.style.left) / 100,
      startY: parseFloat(element.style.top) / 100,
      tooltip: element.querySelector('.planet-tooltip'),
      tooltipWidth: 0
    }));
    let width = 0;
    let height = 0;
    let orbitFrame = 0;
    let elapsed = 0;
    let lastTime = 0;
    let hovering = false;
    let touching = false;

    function positionPlanets() {
      const rotation = elapsed / 108000 * Math.PI * 2;
      planets.forEach(planet => {
        const angle = planet.phase + rotation;
        const x = (300 + planet.radius * Math.cos(angle) * Math.cos(tilt)
          - planet.radius * .65 * Math.sin(angle) * Math.sin(tilt)) / 600 * width;
        const y = (275 + planet.radius * Math.cos(angle) * Math.sin(tilt)
          + planet.radius * .65 * Math.sin(angle) * Math.cos(tilt)) / 550 * height;
        planet.element.style.translate = `${x - planet.startX * width}px ${y - planet.startY * height}px`;
        const halfTip = planet.tooltipWidth / 2;
        const shift = Math.max(halfTip - x, Math.min(0, width - halfTip - x));
        planet.element.style.setProperty('--tooltip-shift', `${shift}px`);
      });
    }

    function canOrbit() {
      return !paused && !reducedMotion.matches && !document.hidden
        && !solar.classList.contains('is-offscreen') && !hovering && !touching
        && !solar.contains(document.activeElement);
    }

    function orbit(time) {
      orbitFrame = 0;
      if (!canOrbit()) return;
      // Pause time is excluded, so returning to the scene never causes a jump.
      elapsed += Math.min(time - lastTime, 80);
      lastTime = time;
      positionPlanets();
      orbitFrame = requestAnimationFrame(orbit);
    }

    syncOrbit = () => {
      if (canOrbit()) {
        if (!orbitFrame) {
          lastTime = performance.now();
          orbitFrame = requestAnimationFrame(orbit);
        }
      } else {
        cancelAnimationFrame(orbitFrame);
        orbitFrame = 0;
      }
    };

    function resizeOrbit() {
      width = scene.clientWidth;
      height = scene.clientHeight;
      planets.forEach(planet => { planet.tooltipWidth = planet.tooltip.offsetWidth; });
      positionPlanets();
    }
    const orbitResize = 'ResizeObserver' in window ? new ResizeObserver(resizeOrbit) : null;
    orbitResize?.observe(scene);
    window.addEventListener('resize', resizeOrbit, { passive: true });
    solar.addEventListener('pointerenter', event => {
      hovering = event.pointerType === 'mouse';
      syncOrbit();
    });
    solar.addEventListener('pointerleave', () => { hovering = false; syncOrbit(); });
    solar.addEventListener('pointerdown', () => { touching = true; syncOrbit(); });
    const releasePointer = () => { touching = false; syncOrbit(); };
    window.addEventListener('pointerup', releasePointer);
    window.addEventListener('pointercancel', releasePointer);
    solar.addEventListener('focusin', () => syncOrbit());
    solar.addEventListener('focusout', () => queueMicrotask(syncOrbit));
    window.addEventListener('pagehide', () => {
      cancelAnimationFrame(orbitFrame);
      orbitFrame = 0;
    });
    window.addEventListener('pageshow', () => { resizeOrbit(); syncOrbit(); });
    resizeOrbit();
    syncOrbit();

    scene.addEventListener('pointermove', event => {
      if (event.pointerType === 'mouse' && !hovering) { hovering = true; syncOrbit(); }
    }, { passive: true });
  }

  // The middle GPU defines a common horizontal axis. CSS handles the short
  // timeline; a fresh random destination is selected at each request boundary.
  document.querySelectorAll('.art-inference-routing').forEach(art => {
    const wires = art.querySelector('.routing-wires');
    if (!wires) return;
    const gpuNodes = [...art.querySelectorAll('.gpu-stack>span')];
    const outgoingPacket = art.querySelector('.routing-packet-out');
    const incomingPacket = art.querySelector('.routing-packet-in');
    const card = art.closest('.project-card');
    let selectedIndex = 0;
    let exploring = false;
    let paths = [];

    const chooseRoute = () => {
      selectedIndex = Math.floor(Math.random() * gpuNodes.length);
      art.dataset.routingTarget = String(selectedIndex + 1);
      gpuNodes.forEach((node, index) => node.classList.toggle('gpu-selected', index === selectedIndex));
      if (paths[selectedIndex]) outgoingPacket.setAttribute('d', paths[selectedIndex]);
    };
    const drawRoutes = () => {
      const bounds = art.getBoundingClientRect();
      const origin = {left:bounds.left + art.clientLeft,top:bounds.top + art.clientTop,width:art.clientWidth,height:art.clientHeight};
      if (!origin.width || !origin.height) return;
      const inputNode = art.querySelector('.routing-input');
      const hubNode = art.querySelector('.routing-hub');
      const input = inputNode.getBoundingClientRect();
      const hub = hubNode.getBoundingClientRect();
      const gpus = gpuNodes.map(node => node.getBoundingClientRect());
      const middleY = gpus[1].top + gpus[1].height / 2 - origin.top;
      inputNode.style.top = `${middleY - input.height / 2}px`;
      hubNode.style.top = `${middleY - hub.height / 2}px`;
      const startX = input.right - origin.left + 6;
      const hubLeft = hub.left - origin.left;
      const hubRight = hub.right - origin.left;
      const inbound = `M${startX} ${middleY} H${hubLeft}`;
      wires.setAttribute('viewBox', `0 0 ${origin.width} ${origin.height}`);
      art.querySelector('.routing-wire-in').setAttribute('d', inbound);
      incomingPacket.setAttribute('d', inbound);
      paths = gpus.map((gpu, index) => {
        const endX = gpu.left - origin.left;
        const endY = gpu.top + gpu.height / 2 - origin.top;
        const branchX = hubRight + (endX - hubRight) * .64;
        const path = index === 1 ? `M${hubRight} ${middleY} H${endX}`
          : `M${hubRight} ${middleY} H${branchX} V${endY} H${endX}`;
        art.querySelector(`.routing-wire-${index + 1}`).setAttribute('d', path);
        return path;
      });
      outgoingPacket.setAttribute('d', paths[selectedIndex]);
    };

    if (card) {
      const syncExploration = () => {
        const active = card.matches(':hover') || card.contains(document.activeElement);
        if (active && !exploring) chooseRoute();
        exploring = active;
      };
      card.addEventListener('pointerenter', syncExploration);
      card.addEventListener('pointerleave', syncExploration);
      card.addEventListener('focusin', syncExploration);
      card.addEventListener('focusout', () => queueMicrotask(syncExploration));
      incomingPacket.addEventListener('animationiteration', event => {
        if (event.animationName === 'routing-arrival' && exploring) chooseRoute();
      });
      syncExploration();
    }
    if ('ResizeObserver' in window) new ResizeObserver(drawRoutes).observe(art);
    else window.addEventListener('resize', drawRoutes, { passive: true });
    document.fonts.ready.then(drawRoutes);
    drawRoutes();
  });

  const description = document.getElementById('skill-description');
  const skillNodes = [...document.querySelectorAll('.constellation-node')];
  const skillConnections = [...document.querySelectorAll('.constellation-map line')];
  skillNodes.forEach(node => {
    node.setAttribute('aria-pressed', 'false');
    let pointerType = '';
    function select(touchLabel = false) {
      skillNodes.forEach(other => {
        other.setAttribute('aria-pressed', String(other === node));
        other.toggleAttribute('data-touch-label', touchLabel && other === node);
      });
      skillConnections.forEach(connection => {
        connection.classList.toggle('is-active', connection.dataset.from === node.dataset.node || connection.dataset.to === node.dataset.node);
      });
      if (description) description.textContent = `${node.dataset.skill} — ${node.dataset.description}`;
    }
    node.addEventListener('pointerdown', event => { pointerType = event.pointerType; });
    node.addEventListener('click', event => select((event.pointerType || pointerType) === 'touch'));
    node.addEventListener('focus', () => select());
    node.addEventListener('pointerenter', event => {
      if (event.pointerType === 'mouse') select();
    });
  });

  // Close the mobile disclosure when traversing native browser history.
  window.addEventListener('hashchange', () => closeMenu());
})();
