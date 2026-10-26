# Implementation audit and review

## Initial audit

The repository was a static HTML/CSS/JavaScript portfolio, not Next.js or React. It had no package manifest, TypeScript, build command, test infrastructure, 3D scene, or local résumé PDF. The homepage used an older identity, location, employment dates, contact links, generic project thumbnails, a large portrait, and a typewriter introduction. Legacy detail pages relied on `assets/css/style.css` and `assets/js/main.js`.

The redesign replaces the homepage and adds dedicated universe assets, while retaining the legacy files and project routes. It preserves earlier experience and certification references through expandable archive sections. The supplied verified profile takes precedence over conflicting older homepage content.

## Implementation choices

- Retain the static stack. Introducing React, Three.js, and a dependency pipeline solely for navigation would add considerable complexity to this repository. Layered gradients, SVG orbital paths, and native links produce a dimensional miniature solar system that does not require WebGL.
- Use three tilted orbital paths with a shared 108-second clock to keep planets spaced. Surface textures rotate independently. Large native anchors remain upright, and orbital motion pauses during pointer approach, touch, keyboard focus, and offscreen/hidden-page states. Paused time is excluded so resuming does not jump forward. Reduced-motion users receive a static scene.
- Render important content as HTML at build time, keeping profile content in JSON. Core content and conventional navigation also work without JavaScript.
- Use real project pages instead of modals, preserving history, deep links, and ordinary keyboard behavior.
- Keep employer and independent projects distinct. Diagrams are conceptual and derived from the supplied descriptions; engineering considerations are framed as tradeoffs rather than unsupported implementation claims.
- Use the user-confirmed current résumé at `assets/documents/resume.pdf` for viewing and downloading, with the filename `MURTAZA_ZAIDI_RESUME.pdf`. The document-folder PDF takes priority over root-level copies.

## Design review 1: visual quality

Reviewed actual desktop, tablet, mobile, and project screenshots. Kept a restrained starfield and faint atmospheric gradients so the introduction stays dominant. Fixed the intended lavender name accent, balanced planet lighting with the warm central star, and aligned project-card actions despite varying copy lengths. Used original diagrams in place of unrelated stock imagery.

## Design review 2: recruiter usability

Increased accomplishment and project-body text sizes, enlarged planet labels and the motion control, simplified tablet navigation, and preserved a visible résumé action on small screens. The first viewport identifies the engineer, specializations, work CTA, résumé CTA, and location. The measured experience results are attributed to the correct employer. Mobile menu selection moves keyboard focus to the destination; Escape restores focus to the menu trigger.

## Engineering review

Build/content checks validate IDs, heading structure, local links/assets, fragments, résumé bytes, important verified facts, and production packaging. Real Chrome tests validate the five requested viewport widths, navigation, actual keyboard/touch events, case studies and browser Back, accessible control names, reduced motion, persisted pause settings, hidden/offscreen lifecycle, and no-JavaScript/WebGL-disabled operation.

Screenshots and the machine-readable browser report are generated under `artifacts/`. Browser measurements are local test observations; no Lighthouse or field performance score is claimed. The remaining limitations and deployment instructions are in `README.md`.
