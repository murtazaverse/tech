#!/usr/bin/env python3
"""Render the portfolio with Python's standard library. No runtime dependencies."""
import argparse
import html
import json
import math
import os
from pathlib import Path
import shutil
from string import Template
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / 'content/profile.json').read_text())
ARCHIVE = json.loads((ROOT / 'content/archive.json').read_text())
P = DATA['profile']


def e(value):
    return html.escape(str(value), quote=True)


def render(template_name, **values):
    return Template((ROOT / 'templates' / template_name).read_text()).substitute(values)


def tags(items):
    return '<ul class="tags">' + ''.join(f'<li>{e(x)}</li>' for x in items) + '</ul>'


def resume(prefix=''):
    for name in ('resume.pdf', 'MURTAZA_ZAIDI_RESUME.pdf'):
        if (ROOT / name).exists():
            return prefix + name, True
    return prefix + 'assets/documents/resume.pdf', False


def header(prefix='', home=True):
    base = '' if home else prefix + 'index.html'
    nav = ''.join(f'<a href="{base}#{slug}" data-section="{slug}">{label}</a>' for slug, label in [('home','Home'),('experience','Experience'),('projects','Projects'),('skills','Skills'),('education','Education'),('contact','Contact')])
    return f'''<a class="skip-link" href="#main">Skip to content</a>
    <header class="site-header"><div class="container header-inner">
      <a class="brand" href="{base}#home" aria-label="Murtazaverse home"><span class="brand-mark" aria-hidden="true">✳</span> murtazaverse<span class="brand-period">.</span></a>
      <nav class="desktop-nav" aria-label="Main navigation">{nav}</nav>
      <a class="header-resume" href="{base}#resume">Resume <span aria-hidden="true">↗</span></a>
      <button class="menu-toggle" aria-expanded="false" aria-controls="mobile-nav" aria-label="Open navigation" hidden><span></span><span></span></button>
    </div><nav id="mobile-nav" class="mobile-nav" aria-label="Mobile navigation" hidden>{nav}</nav></header><noscript><nav class="nojs-nav container" aria-label="Section navigation">{nav}</nav></noscript>'''


def footer(prefix='', home=True):
    base = '' if home else prefix + 'index.html'
    return f'''<footer class="site-footer container"><a class="brand" href="{base}#home"><span class="brand-mark" aria-hidden="true">✳</span> murtazaverse.</a><p>A small universe. An endless curiosity.</p><a href="{base}#home">Back to Earth ↑</a><span>© 2026 {e(P['name'])}</span></footer>'''


def head(title, description, prefix='', page=''):
    domain = os.environ.get('MURTAZAVERSE_SITE_URL', '').rstrip('/')
    if domain and (urlparse(domain).scheme not in ('https', 'http') or not urlparse(domain).netloc):
        raise ValueError('MURTAZAVERSE_SITE_URL must be an absolute http(s) URL')
    canonical = f'<link rel="canonical" href="{e(domain + "/" + page)}">' if domain else ''
    image = domain + '/assets/img/social-preview.png' if domain else prefix + 'assets/img/social-preview.png'
    return f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="dark"><meta name="theme-color" content="#080c18">
    <title>{e(title)}</title><meta name="description" content="{e(description)}"><meta name="author" content="{e(P['name'])}">
    <meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:site_name" content="Murtazaverse"><meta property="og:image" content="{e(image)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Murtazaverse — Murtaza, AI & Software Engineer"><meta name="twitter:card" content="summary_large_image">
    {canonical}<link rel="icon" type="image/svg+xml" href="{prefix}assets/img/favicon.svg">
    <link rel="preload" href="{prefix}assets/fonts/space-grotesk.woff2" as="font" type="font/woff2" crossorigin>
    <link rel="stylesheet" href="{prefix}assets/css/universe.css"><script src="{prefix}assets/js/universe.js" defer></script>'''


PLANETS = [
    ('origin', 'Origin', 'about', 'A little context on the human behind the code.'),
    ('career', 'Career Orbit', 'experience', 'Organizations that trusted me with production.'),
    ('project', 'Project Nebula', 'projects', 'Small ideas. Real engineering.'),
    ('tech', 'Tech Constellation', 'skills', 'Tools currently aboard the spaceship.'),
    ('academic', 'Academic Outpost', 'education', 'Where curiosity becomes research.'),
    ('signal', 'Signal Station', 'contact', 'Friendly Earthlings welcome.')
]


def sparkles():
    stars = [(7,12,5.7,-2.1),(18,76,7.3,-5.4),(29,8,6.1,-.8),(36,58,8.7,-4.2),
             (45,28,4.9,-3.7),(53,86,7.9,-1.6),(61,12,6.7,-5.8),(67,52,9.1,-2.9),
             (75,79,5.3,-4.6),(82,18,8.1,-6.3),(91,39,6.3,-1.2),(96,89,7.1,-3.4)]
    return '<div class="star-sparkles">' + ''.join(
        f'<span class="sparkle" style="--x:{x}%;--y:{y}%;--sparkle-duration:{duration}s;--sparkle-delay:{delay}s"></span>'
        for x,y,duration,delay in stars) + '</div>'


def solar():
    tracks = {'origin':(248,240), 'career':(215,300), 'project':(232,0),
              'tech':(248,60), 'academic':(215,120), 'signal':(232,180)}
    tilt = math.radians(-28)
    links = []
    for kind,label,target,tip in PLANETS:
        radius, phase = tracks[kind]
        angle = math.radians(phase)
        x = 300 + radius * math.cos(angle) * math.cos(tilt) - radius * .65 * math.sin(angle) * math.sin(tilt)
        y = 275 + radius * math.cos(angle) * math.sin(tilt) + radius * .65 * math.sin(angle) * math.cos(tilt)
        links.append(f'''<a class="planet planet-{kind}" href="#{target}" style="left:{x/6:.5f}%;top:{y/5.5:.5f}%" data-orbit-radius="{radius}" data-orbit-phase="{phase}" aria-label="{label}: go to {target}"><span class="planet-sphere" aria-hidden="true"></span><span class="planet-label">{label}</span><span class="planet-tooltip" aria-hidden="true">{e(tip)}</span></a>''')
    return f'''<div class="solar" aria-label="Explore Murtazaverse through six planetary navigation links">
      <div class="scene-top"><span class="mono">A LITTLE UNIVERSE, BUILT WITH CURIOSITY</span><button class="motion-toggle" type="button" aria-pressed="false" aria-label="Pause decorative motion" hidden><span aria-hidden="true">Ⅱ</span></button></div>
      <div class="solar-scene"><div class="scene-halo" aria-hidden="true"></div>
      <svg class="orbits" viewBox="0 0 600 550" fill="none" aria-hidden="true"><g transform="rotate(-28 300 275)"><ellipse cx="300" cy="275" rx="248" ry="161.2"/><ellipse cx="300" cy="275" rx="232" ry="150.8"/><ellipse cx="300" cy="275" rx="215" ry="139.75"/><ellipse class="orbit-dashed" cx="300" cy="275" rx="270" ry="180"/></g><g class="orbit-dots"><circle cx="101" cy="340" r="2"/><circle cx="405" cy="103" r="2"/><circle cx="493" cy="357" r="2"/><path d="M533 149v10m-5-5h10M91 180v8m-4-4h8M388 452v8m-4-4h8"/></g></svg>
      <a class="sun" href="#about" aria-label="Meet Murtaza"><span class="sun-surface" aria-hidden="true">m<span>✳</span></span></a>{''.join(links)}
      </div><p class="scene-caption"><span class="tiny-star" aria-hidden="true">✧</span> Six destinations. One curious engineer. <span class="caption-hint">Pick a planet ↗</span></p></div>'''


def experience():
    out = []
    for i, item in enumerate(DATA['experience']):
        out.append(f'''<article class="experience-card {item['color']} reveal"><div class="experience-meta"><div class="company-line"><span class="company-mark" aria-hidden="true">{e(item['mark'])}</span><h3>{e(item['company'])}</h3>{'<span class="current-badge">Current orbit</span>' if i == 0 else ''}</div><p class="job-date">{e(item['dates'])}</p><p class="job-location">{e(item['location'])}</p></div><div class="experience-body"><h4>{e(item['role'])}</h4><p>{e(item['summary'])}</p><ul class="achievements">{''.join('<li>'+e(b)+'</li>' for b in item['bullets'])}</ul>{tags(item['stack'])}</div></article>''')
    earlier = ''.join(f'<article><h4>{e(x["role"])} · {e(x["company"])}</h4><p class="mono">{e(x["dates"])}</p><p>{e(x["summary"])}</p></article>' for x in DATA['earlier_experience'])
    return ''.join(out) + f'<details class="archive"><summary>Earlier chapters <span>Internships & early engineering experience +</span></summary><div class="earlier-grid">{earlier}</div></details>'


def art(project, large=False):
    slug = project['slug']
    if slug == 'data-man':
        body = '<div class="art-orbit"></div><div class="data-query"><span class="query-spark">✳</span> Ask a question about your data <span>↗</span></div><div class="data-flow"><span>Schema<br><b>context</b></span><i>→</i><span class="flow-core">SQL + ETL<br><b>agents</b></span><i>→</i><span>Structured<br><b>answers</b></span></div><div class="chart-bars">'+''.join(f'<i style="--bar:{x}%"></i>' for x in [23,37,32,56,46,65,60,81,74,94])+'</div><span class="art-caption">QUESTION → CONTEXT → INSIGHT</span>'
    elif slug == 'kira':
        body = '<div class="agent-orbit orbit-one"></div><div class="agent-orbit orbit-two"></div><span class="agent-node node-a">Spend analysis</span><span class="agent-node node-b">Vendor insights</span><span class="agent-node node-c">Document retrieval</span><div class="agent-core">kira<span>AI procurement assistant</span></div><span class="art-caption">THE RIGHT AGENT FOR THE QUESTION</span>'
    elif slug == 'patent-search':
        body = '<div class="patent-doc doc-back"><i></i><i></i><i></i></div><div class="patent-doc doc-front"><span>Patent evidence</span><i></i><i class="highlight"></i><i></i><i class="highlight short"></i><i></i><div class="doc-check">✓ &nbsp; Structured output</div></div><div class="search-lens"></div><span class="art-caption">FROM TECHNICAL DOCUMENTS TO EVIDENCE</span>'
    else:
        body = '<svg class="routing-wires" viewBox="0 0 600 240" fill="none"><path class="routing-wire routing-wire-in" d="M150 110H214"/><path class="routing-wire routing-wire-1" d="M302 110H385V57H430"/><path class="routing-wire routing-wire-2" d="M302 110H385V101H430"/><path class="routing-wire routing-wire-3" d="M302 110H385V145H430"/><path class="routing-packet routing-packet-in" pathLength="100" d="M150 110H214"/><path class="routing-packet routing-packet-out" pathLength="100" d="M302 110H385V145H430"/></svg><div class="routing-input">LLM requests</div><div class="routing-hub">Placement<br><b>layer</b><span class="routing-thinking"><i></i><i></i><i></i></span></div><div class="gpu-stack"><span><i></i> GPU tier 01</span><span><i></i> GPU tier 02</span><span><i></i> GPU tier 03</span></div><span class="research-label">↗ Research in progress</span><span class="art-caption">LATENCY · FINANCIAL COST · ENERGY</span>'
    return f'<div class="project-art art-{slug} {"art-large" if large else ""}" aria-hidden="true">{body}</div>'


def projects():
    return ''.join(f'''<article class="project-card {p['color']} reveal">{art(p)}<div class="project-body"><div class="project-meta"><span>{e(p['type'])}</span><span aria-hidden="true">0{i+1}</span></div><h3><a class="project-link" href="projects/{p['slug']}.html">{e(p['name'])}<span class="project-arrow" aria-hidden="true">↗</span></a></h3><p>{e(p['description'])}</p><p class="project-contribution">{e(p['contribution'])}</p><div class="project-bottom">{tags(p['preview_stack'])}<span class="case-label" aria-hidden="true">View case study ↗</span></div></div></article>''' for i,p in enumerate(DATA['projects']))


def skills():
    return ''.join(f'<article class="skill-card {x["color"]}"><h3><span class="skill-dot" aria-hidden="true"></span>{e(x["name"])}</h3>{tags(x["items"])}</article>' for x in DATA['skills'])


def constellation():
    graph = DATA['constellation']
    nodes = {node['id']: node for node in graph['nodes']}
    legend = '<ul class="constellation-legend" aria-label="Skill groups">' + ''.join(
        f'<li class="{e(group["color"])}"><span class="skill-dot" aria-hidden="true"></span>{e(group["name"])}</li>'
        for group in graph['groups']) + '</ul>'
    lines = []
    for source, target in graph['connections']:
        start, end = nodes[source], nodes[target]
        lines.append(f'<line data-from="{e(source)}" data-to="{e(target)}" x1="{start["x"]}" y1="{start["y"]}" x2="{end["x"]}" y2="{end["y"]}"/>')
    buttons = ''.join(
        f'<button class="constellation-node {e(node["color"])}" type="button" style="--x:{node["x"]}%;--y:{node["y"]}%" data-node="{e(node["id"])}" data-skill="{e(node["name"])}" data-description="{e(node["description"])}" aria-describedby="skill-description"><span aria-hidden="true"></span>{e(node["name"])}</button>'
        for node in nodes.values())
    return f'<div class="constellation">{legend}<div class="constellation-map"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{"".join(lines)}</svg>{buttons}</div><p id="skill-description" aria-live="polite">Select a star to explore the ideas and tools behind my work.</p></div>'


def education():
    return ''.join(f'<article class="education-card reveal"><img src="{e(x["logo"])}" alt="" width="48" height="48" loading="lazy"><div><p class="mono">{e(x["institution"])}</p><h3>{e(x["degree"])}</h3><p class="grade">GPA <strong>{e(x["grade"])}</strong> · German grading scale</p></div></article>' for x in DATA['education'])


def archive():
    projects = ''.join(f'<a href="{e(x["href"])}"><span>{e(x["name"])}</span><span>{e(x["category"])} ↗</span></a>' for x in ARCHIVE['projects'])
    certs = ''.join(f'<a href="{e(x["href"])}" target="_blank" rel="noopener noreferrer"><span>{e(x["name"])}</span><span>{e(x["issuer"])} ↗</span></a>' for x in ARCHIVE['certifications'])
    return f'<details class="archive"><summary>More experiments from the archive <span>Computer vision, ML & engineering +</span></summary><div class="archive-links">{projects}</div></details>', f'<details class="archive"><summary>Always a student <span>Selected certifications +</span></summary><div class="archive-links">{certs}</div></details>'


def build():
    archived, certs = archive()
    resume_url, current_resume = resume()
    resume_text = 'My experience, skills, and education in one place.' if current_resume else 'The existing PDF is an earlier version. This website reflects my current experience; email me for my latest résumé.'
    resume_label = 'Download resume' if current_resume else 'Download previous résumé'
    title = 'Murtaza | AI & Software Engineer — Murtazaverse'
    desc = 'Explore Murtazaverse, the interactive portfolio of Murtaza, an AI and Software Engineer building AI agents, reliable backends, and data-driven products.'
    profile_schema = {'@context':'https://schema.org','@type':'Person','name':P['name'],'jobTitle':P['role'],'email':P['email'],'sameAs':[P['github'],P['linkedin']],'homeLocation':{'@type':'Place','name':P['location']}}
    index = render('index.html',head=head(title,desc),header=header(),footer=footer(),sparkles=sparkles(),solar=solar(),experience=experience(),projects=projects(),skills=skills(),constellation=constellation(),education=education(),archived=archived,certifications=certs,email=e(P['email']),phone=e(P['phone']),phone_tel=e(P['phone'].replace(' ','')),github=e(P['github']),linkedin=e(P['linkedin']),location=e(P['location']),resume_url=e(resume_url),resume_text=e(resume_text),resume_label=e(resume_label),resume_filename='MURTAZA_ZAIDI_RESUME.pdf' if current_resume else 'MURTAZA_ZAIDI_PREVIOUS_RESUME.pdf',profile_schema=json.dumps(profile_schema).replace('<','\\u003c'))
    (ROOT / 'index.html').write_text(index)
    for i, p in enumerate(DATA['projects']):
        next_p = DATA['projects'][(i+1) % len(DATA['projects'])]
        flow = '<ol class="architecture-flow">'+''.join('<li>'+e(x)+'</li>' for x in p['flow'])+'</ol>'
        body = render('case-study.html',head=head(p['name']+' — Murtazaverse',p['description'],'../','projects/'+p['slug']+'.html'),header=header('../',False),footer=footer('../',False),sparkles=sparkles(),name=e(p['name']),subtitle=e(p['subtitle']),project_type=e(p['type']),status=e(p['status']),description=e(p['description']),art=art(p,True),problem=e(p['problem']),solution=e(p['solution']),contributions=''.join('<li>'+e(x)+'</li>' for x in p['contributions']),flow=flow,considerations=''.join('<li>'+e(x)+'</li>' for x in p['considerations']),outcome=e(p['outcome']),stack=tags(p['stack']),next_url=next_p['slug']+'.html',next_name=e(next_p['name']),color=p['color'],work_note='<p class="case-note">Professional work. This case study describes my contributions at a high level; internal code and implementation details are not shared.</p>' if 'Professional' in p['type'] else '')
        (ROOT / 'projects' / (p['slug']+'.html')).write_text(body)
    domain = os.environ.get('MURTAZAVERSE_SITE_URL','').rstrip('/')
    robots = 'User-agent: *\nAllow: /\n'
    if domain:
        pages = ['', *('projects/'+p['slug']+'.html' for p in DATA['projects'])]
        (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+e(domain+'/'+x)+'</loc></url>' for x in pages)+'</urlset>')
        robots += 'Sitemap: '+domain+'/sitemap.xml\n'
    elif (ROOT/'sitemap.xml').exists():
        (ROOT/'sitemap.xml').unlink()
    (ROOT/'robots.txt').write_text(robots)


def package():
    destination = ROOT/'dist'
    destination.mkdir(exist_ok=True)
    for name in ('assets','projects'):
        shutil.copytree(ROOT/name,destination/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.DS_Store'))
    for name in ('index.html','favicon.png','m.png','robots.txt','sitemap.xml','resume.pdf','MURTAZA_ZAIDI_RESUME.pdf'):
        if (ROOT/name).exists():
            shutil.copy2(ROOT/name,destination/name)
        elif (destination/name).is_file():
            (destination/name).unlink()
    print('Built static portfolio and 4 case studies → dist/')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-only',action='store_true')
    args = parser.parse_args()
    build()
    if not args.render_only:
        package()
