# Murtazaverse

Murtaza Zaidi’s portfolio: a small interactive universe for AI engineering, backend systems, and data products. It runs as a static website with local fonts, native planetary links, and four statically rendered engineering case studies. No JavaScript framework or package installation is required.

## Run locally

Requires Python 3.10 or newer.

```sh
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

Open <http://localhost:8000>. The checked-in `index.html` also works with an ordinary static server at the repository root. Rebuild after changing content or templates. Build output is in `dist/` and is ignored by Git.

## Content and components

- `content/profile.json`: the supplied verified profile, exact employment dates and results, case-study content, skills, education, and outstanding assets.
- `content/archive.json`: all 11 pre-existing projects and six certifications.
- `templates/index.html`: hero, experience, projects, skills, education, contact, and résumé sections.
- `templates/case-study.html`: reusable project pages, with conceptual architecture, individual contributions, design considerations, and verified outcomes.
- `scripts/build.py`: standard-library static renderer; shared navigation, solar system, project illustrations, skill constellation, metadata, and deployment output.
- `assets/css/universe.css`: space environment, textured CSS planets, responsive layouts, project diagrams, print styles, and reduced-motion support.
- `assets/js/universe.js`: mobile disclosure, active-section tracking, page-wide cursor glow, focusable skill nodes, scroll reveals, and animation lifecycle controls.
- `assets/fonts/`: self-hosted Space Grotesk and DM Sans variable fonts with SIL Open Font License files.
- `assets/img/social-preview.png`: original social-sharing card; its reproducible source is `templates/social-preview.html`.
- `assets/img/background/`: the ESO Milky Way panorama, asteroids, and locally stored NASA planet photographs. Sources and credits are in `CREDITS.md`, with a visible Milky Way credit in every footer. Scrolling reveals Saturn on the left, Earth in the center, Mars on the left, and Pluto on the right. Small vector rockets, satellites, and UFOs drift in the background; only powered craft have exhaust. Mobile layouts show one of each craft. Reduced motion disables parallax and exhaust, and the motion control freezes all decoration.

Generated HTML is included for ordinary static hosting. Edit the content/templates rather than the generated pages. The existing project pages, their shared CSS/JavaScript, images, and other assets are preserved.

## Résumé and remaining assets

The current résumé is `assets/documents/resume.pdf`. Both the PDF viewer and download action use this file. Downloads are named `MURTAZA_ZAIDI_RESUME.pdf`.

Replace `assets/documents/resume.pdf` and rebuild when updating the résumé. This document-folder file takes priority over any older copies in the repository root.

Also outstanding:

- Production domain: configure it at build time as described below.
- Degree dates and exact thesis title/submission date: omitted because the verified profile does not supply them.
- Individual project repositories and live demos: omitted until real URLs are supplied.
- Product screenshots: original conceptual diagrams are used instead. Employer case studies are explicitly identified as professional work and describe only the supplied high-level contributions.

The thesis is consistently presented as research in progress. No completed cost, latency, or energy improvement is claimed.

## Validation

```sh
python3 scripts/build.py
python3 -m unittest discover -s tests -p 'check_*.py' -v
python3 -m py_compile scripts/build.py tests/check_site.py tests/browser.py
python3 tests/browser.py
```

The browser suite requires Google Chrome/Chromium and permission to bind local sockets. It uses Python’s standard library and Chrome DevTools Protocol, launches an isolated browser with WebGL disabled, and stops its server and browser on exit. It creates screenshots and a JSON report in the ignored `artifacts/` directory. It also regenerates the social-sharing image and builds the site.

Checks cover the 1440, 1280, 768, 390, and 320px layouts, local destinations and fragments, preserved content, résumé delivery, six planetary links, all four case studies, native browser history, keyboard/touch navigation, focus management, accessible control names, motion preferences, animation suspension, and no-JavaScript rendering. Browser runs report runtime/console errors and failed requests. Local performance timings are diagnostic observations, not Lighthouse scores or field Core Web Vitals results.

There was no package manager, lint script, TypeScript configuration, or test framework in the original project. No production dependencies were added. The focused Python checks and real Chrome interaction tests are the validation path for this static stack. Lighthouse, other browser engines, and manual screen-reader testing have not been run.

The supplied GitHub profile and four of the six preserved certification links responded successfully during live checks. LinkedIn returned its automation-blocking status (999), and the two DataCamp pages returned 403; these destinations are retained without claiming their authenticated content was verified. The old Udemy short link was updated to its observed HTTPS destination.

## Deploy

No source was committed or pushed, and no remote site was published during this redesign.

1. Confirm the current résumé in `assets/documents/resume.pdf` and any remaining optional content.
2. Set `MURTAZAVERSE_SITE_URL` to the real HTTPS origin when building. This adds canonical URLs, an absolute social-preview URL, a sitemap, and a sitemap reference in `robots.txt`.
3. Run the checks above and upload the contents of `dist/` to a static host, or configure your existing host to run `python3 scripts/build.py` and serve `dist/`.

Without a known domain, no canonical or sitemap with an invented hostname is generated. This app has no SPA routing requirement: case studies are ordinary HTML files.
