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
- `assets/js/universe.js`: mobile disclosure, active-section tracking, scene-only pointer glow, focusable skill nodes, scroll reveals, and animation lifecycle controls.
- `assets/fonts/`: self-hosted Space Grotesk and DM Sans variable fonts with SIL Open Font License files.
- `assets/img/social-preview.png`: original social-sharing card; its reproducible source is `templates/social-preview.html`.

Generated HTML is included for ordinary static hosting. Edit the content/templates rather than the generated pages. The existing project pages, their shared CSS/JavaScript, images, and other assets are preserved.

## Résumé and remaining assets

**TODO: supply the current résumé PDF.** The existing Google Drive résumé was retrieved and inspected. It predates the supplied verified profile and contains older contact details, so it is preserved as `assets/documents/previous-resume.pdf`, explicitly labeled as an earlier version in the UI. It is not presented as the current résumé.

Place the current PDF at `resume.pdf` or `MURTAZA_ZAIDI_RESUME.pdf` in the repository root, then rebuild. The renderer automatically uses that file, updates the labels, and enables the current résumé download filename.

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

1. Add the current résumé and confirm any remaining optional content.
2. Set `MURTAZAVERSE_SITE_URL` to the real HTTPS origin when building. This adds canonical URLs, an absolute social-preview URL, a sitemap, and a sitemap reference in `robots.txt`.
3. Run the checks above and upload the contents of `dist/` to a static host, or configure your existing host to run `python3 scripts/build.py` and serve `dist/`.

Without a known domain, no canonical or sitemap with an invented hostname is generated. This app has no SPA routing requirement: case studies are ordinary HTML files.
