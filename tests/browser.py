#!/usr/bin/env python3
"""Chrome smoke tests and screenshots, using a small stdlib-only CDP client.

Run: python3 tests/browser.py (requires google-chrome and local socket access).
The owned HTTP server and Chrome process are stopped on exit.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import time
from urllib.request import urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT/'artifacts'
ARTIFACTS.mkdir(exist_ok=True)


class CDP:
    def __init__(self, url):
        parsed = urlparse(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=15)
        self.socket.settimeout(20)
        key = base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall((f'GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        response = b''
        while not response.endswith(b'\r\n\r\n'):
            response += self.socket.recv(1)
        assert response.startswith(b'HTTP/1.1 101 '), response
        accept = base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        assert accept in response
        self.counter = 0
        self.events = []

    def read(self, count):
        data = b''
        while len(data) < count:
            part = self.socket.recv(count-len(data))
            if not part:
                raise ConnectionError('Chrome closed the debugging connection')
            data += part
        return data

    def receive(self):
        message = b''
        while True:
            first, second = self.read(2)
            size = second & 127
            if size == 126:
                size = struct.unpack('!H', self.read(2))[0]
            elif size == 127:
                size = struct.unpack('!Q', self.read(8))[0]
            mask = self.read(4) if second & 128 else None
            data = self.read(size)
            if mask:
                data = bytes(value ^ mask[i % 4] for i, value in enumerate(data))
            if first & 15 == 8:
                raise ConnectionError('WebSocket closed')
            message += data
            if first & 128:
                return json.loads(message)

    def call(self, method, params=None):
        self.counter += 1
        data = json.dumps({'id':self.counter,'method':method,'params':params or {}}).encode()
        mask = os.urandom(4)
        length = len(data)
        header = bytes([129, 128 | length]) if length < 126 else bytes([129,254])+struct.pack('!H',length) if length < 65536 else bytes([129,255])+struct.pack('!Q',length)
        self.socket.sendall(header+mask+bytes(value ^ mask[i % 4] for i,value in enumerate(data)))
        while True:
            result = self.receive()
            if result.get('id') == self.counter:
                if 'error' in result:
                    raise RuntimeError(result['error'])
                return result.get('result', {})
            self.events.append(result)

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
        if 'exceptionDetails' in result:
            raise AssertionError(result['exceptionDetails'])
        return result.get('result', {}).get('value')

    def navigate(self, url):
        self.call('Page.navigate', {'url':url})
        for _ in range(100):
            time.sleep(.08)
            try:
                if self.evaluate('document.readyState') == 'complete':
                    self.evaluate('document.fonts.ready.then(() => true)')
                    time.sleep(.15)
                    return
            except RuntimeError:
                continue
        raise TimeoutError(url)

    def viewport(self, width, height=1000, mobile=False):
        self.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':height,'deviceScaleFactor':1,'mobile':mobile})

    def screenshot(self, name, full=False):
        options = {'format':'png','captureBeyondViewport':full}
        if full:
            metrics = self.call('Page.getLayoutMetrics')['cssContentSize']
            options['clip'] = {'x':0,'y':0,'width':metrics['width'],'height':metrics['height'],'scale':1}
        data = self.call('Page.captureScreenshot',options)['data']
        (ARTIFACTS/name).write_bytes(base64.b64decode(data))


def available_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


def wait_http(url):
    for _ in range(100):
        try:
            with urlopen(url, timeout=1) as response:
                return response.read()
        except OSError:
            time.sleep(.1)
    raise TimeoutError(url)


def run():
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    assert chrome, 'Chrome/Chromium is required for browser validation'
    debug_port, http_port = available_port(), available_port()
    processes = []
    report = {'checks': [], 'viewports': [], 'console_errors': [], 'failed_requests': []}

    def check(condition, label):
        assert condition, label
        report['checks'].append(label)
        print('PASS',label,flush=True)

    with tempfile.TemporaryDirectory(prefix='murtazaverse-chrome-') as profile:
        log = (ARTIFACTS/'chrome.log').open('w')
        try:
            processes.append(subprocess.Popen([chrome,'--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-webgl','--disable-background-networking','--no-first-run','--no-default-browser-check',f'--remote-debugging-port={debug_port}',f'--user-data-dir={profile}','about:blank'],stdout=log,stderr=log))
            targets = json.loads(wait_http(f'http://127.0.0.1:{debug_port}/json/list'))
            cdp = CDP(next(t['webSocketDebuggerUrl'] for t in targets if t['type']=='page'))
            cdp.call('Page.enable')
            cdp.call('Runtime.enable')
            cdp.call('Network.enable')
            cdp.call('Log.enable')
            cdp.call('Page.addScriptToEvaluateOnNewDocument',{'source':"window.__localVitals={lcp:0,cls:0};new PerformanceObserver(l=>l.getEntries().forEach(e=>window.__localVitals.lcp=e.startTime)).observe({type:'largest-contentful-paint',buffered:true});new PerformanceObserver(l=>l.getEntries().forEach(e=>{if(!e.hadRecentInput)window.__localVitals.cls+=e.value})).observe({type:'layout-shift',buffered:true});"})

            # Render the original social graphic into a shareable raster image.
            cdp.viewport(1200,630)
            cdp.navigate((ROOT/'templates/social-preview.html').as_uri())
            image = cdp.call('Page.captureScreenshot',{'format':'png'})['data']
            (ROOT/'assets/img/social-preview.png').write_bytes(base64.b64decode(image))
            subprocess.run(['python3','scripts/build.py'],cwd=ROOT,check=True)
            server_log = (ARTIFACTS/'server.log').open('w')
            processes.append(subprocess.Popen(['python3','-m','http.server',str(http_port),'--bind','127.0.0.1','--directory',str(ROOT/'dist')],stdout=server_log,stderr=server_log))
            base = f'http://127.0.0.1:{http_port}'
            check(bool(wait_http(base)), 'Local production server responds successfully')

            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
            for width in (1440,1280,768,390,320):
                cdp.viewport(width,1000 if width>760 else 900,width<=760)
                cdp.navigate(base)
                measurements = cdp.evaluate('''({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,h1:document.querySelector('h1').textContent,planets:document.querySelectorAll('.planet').length,fonts:document.fonts.check('500 20px "Space Grotesk"'),motion:document.documentElement.dataset.motion,cssMotion:getComputedStyle(document.querySelector('.planet-sphere')).animationName})''')
                check(measurements['scrollWidth'] <= width, f'No horizontal overflow at {width}px')
                check(measurements['planets'] == 6, f'Six accessible planet links at {width}px')
                check(measurements['fonts'], f'Local fonts loaded at {width}px')
                check(measurements['motion'] == 'paused' and measurements['cssMotion'] == 'none', f'Reduced motion disables decoration at {width}px')
                check(cdp.evaluate("[...document.querySelectorAll('.sparkle')].every(e=>getComputedStyle(e).animationName==='none') && getComputedStyle(document.querySelector('.planet-sphere'),'::before').animationName==='none'"), f'Reduced motion disables sparkle and surface rotation at {width}px')
                orbit_clipping = cdp.evaluate("""(()=>{
                  const scene=document.querySelector('.solar-scene').getBoundingClientRect(),clipped=[];
                  document.querySelectorAll('[data-orbit-radius]').forEach(planet=>{
                    const ellipse=document.querySelector('.orbits ellipse[rx="'+planet.dataset.orbitRadius+'"]');
                    const bounds=planet.getBoundingClientRect(),length=ellipse.getTotalLength();
                    for(let i=0;i<36;i++){
                      const p=ellipse.getPointAtLength(length*i/36);
                      const point=new DOMPoint(p.x,p.y).matrixTransform(ellipse.getScreenCTM());
                      if(point.x-bounds.width/2<scene.left-1||point.x+bounds.width/2>scene.right+1||point.y-bounds.height/2<scene.top-1||point.y+bounds.height/2>scene.bottom+1){clipped.push(planet.getAttribute('aria-label'));break;}
                    }
                  });
                  return clipped;
                })()""")
                check(not orbit_clipping, f'Planet targets fit throughout a complete orbit at {width}px: {orbit_clipping}')
                network = cdp.evaluate("""(()=>{
                  const map=document.querySelector('.constellation-map').getBoundingClientRect();
                  const nodes=[...document.querySelectorAll('.constellation-node')].map(e=>({name:e.dataset.skill,rect:e.getBoundingClientRect()}));
                  const clipped=nodes.filter(n=>n.rect.left<map.left-1||n.rect.right>map.right+1||n.rect.top<map.top-1||n.rect.bottom>map.bottom+1).map(n=>n.name);
                  const overlapping=[];
                  nodes.forEach((a,i)=>nodes.slice(i+1).forEach(b=>{if(Math.min(a.rect.right,b.rect.right)-Math.max(a.rect.left,b.rect.left)>1&&Math.min(a.rect.bottom,b.rect.bottom)-Math.max(a.rect.top,b.rect.top)>1)overlapping.push([a.name,b.name])}));
                  return {clipped,overlapping};
                })()""")
                check(not network['clipped'] and not network['overlapping'], f'Skill network icons fit without overlap at {width}px: {network}')
                routing_alignment = cdp.evaluate("""(()=>{
                  const art=document.querySelector('.art-inference-routing');
                  const center=selector=>{const r=art.querySelector(selector).getBoundingClientRect();return r.top+r.height/2};
                  const ys=[center('.routing-input'),center('.routing-hub'),center('.gpu-stack>span:nth-child(2)')];
                  const horizontal=selector=>{const p=art.querySelector(selector);return Math.abs(p.getPointAtLength(0).y-p.getPointAtLength(p.getTotalLength()).y)<.1};
                  return Math.max(...ys)-Math.min(...ys)<1&&horizontal('.routing-wire-in')&&horizontal('.routing-wire-2')&&!art.querySelector('.routing-input span');
                })()""")
                check(routing_alignment, f'Request, placement, and middle GPU branch align horizontally at {width}px')
                report['viewports'].append(measurements)
                cdp.screenshot(f'home-{width}.png')
                if width == 1440:
                    report['local_performance'] = cdp.evaluate("({vitals:window.__localVitals,resources:performance.getEntriesByType('resource').map(e=>({name:e.name.split('/').pop(),bytes:e.encodedBodySize,duration:e.duration}))})")
                    cdp.evaluate("document.querySelectorAll('.is-waiting').forEach(e=>e.classList.remove('is-waiting'))")
                    cdp.screenshot('desktop-full.png',True)
                if width == 390:
                    cdp.screenshot('mobile-full.png',True)
                for section_id in ('what-i-do','experience','projects','skills','education','contact','home'):
                    cdp.evaluate(f"document.querySelector('[data-section={section_id}]').click()")
                    time.sleep(.07)
                    landing = cdp.evaluate(f"""(()=>{{
                      const section=document.getElementById('{section_id}'),marker=section.querySelector('.section-index')||section;
                      return {{active:document.querySelector('.desktop-nav [aria-current=location]')?.dataset.section,top:marker.getBoundingClientRect().top,header:document.querySelector('.site-header').getBoundingClientRect().bottom,scroll:scrollY,atBottom:scrollY+innerHeight>=document.documentElement.scrollHeight-2}};
                    }})()""")
                    check(landing['active'] == section_id, f'{section_id} click selects its own navigation dot at {width}px: {landing}')
                    aligned = landing['scroll'] <= 2 if section_id == 'home' else landing['top'] >= landing['header'] and (abs(landing['top']-landing['header']-24)<=3 or landing['atBottom'])
                    check(aligned, f'{section_id} click lands on visible content without an extra scroll at {width}px: {landing}')

            # Exercise actual smooth anchor scrolling, in both navigation layouts.
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]})
            settle_scroll = """new Promise(resolve=>{
              let last=scrollY,stable=0,start=performance.now();
              function tick(){stable=Math.abs(scrollY-last)<.5?stable+1:0;last=scrollY;if(stable>=6||performance.now()-start>2500)resolve(true);else requestAnimationFrame(tick)}
              requestAnimationFrame(tick);
            })"""
            for width in (1440,390):
                cdp.viewport(width,1000 if width>760 else 900,width<=760)
                cdp.navigate(base)
                for section_id in ('skills','education','projects','experience','contact','home'):
                    if width<=760:
                        cdp.evaluate("document.querySelector('.menu-toggle').click()")
                    navigation = '#mobile-nav' if width<=760 else '.desktop-nav'
                    cdp.evaluate(f"document.querySelector('{navigation} [data-section={section_id}]').click()")
                    cdp.evaluate(settle_scroll)
                    check(cdp.evaluate("document.querySelector('.desktop-nav [aria-current=location]')?.dataset.section") == section_id, f'Smooth {section_id} navigation finishes on the correct tab at {width}px')
                cdp.navigate(base+'/#education')
                cdp.evaluate(settle_scroll)
                check(cdp.evaluate("document.querySelector('.desktop-nav [data-section=education]').getAttribute('aria-current')") == 'location', f'Direct Education links select Education without manual scrolling at {width}px')
                cdp.screenshot(f'navigation-education-{width}.png')
                cdp.evaluate("scrollBy({top:-150,behavior:'instant'})")
                time.sleep(.07)
                check(cdp.evaluate("document.querySelector('.desktop-nav [aria-current=location]')?.dataset.section") == 'skills', f'Manual upward scrolling updates the navigation dot at {width}px')
                cdp.evaluate("scrollBy({top:150,behavior:'instant'})")
                time.sleep(.07)
                check(cdp.evaluate("document.querySelector('.desktop-nav [aria-current=location]')?.dataset.section") == 'education', f'Manual downward scrolling restores the Education dot at {width}px')
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})

            # Distinct, cropped planet encounters form a reversible scroll journey.
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]})
            for width in (1440,390):
                cdp.viewport(width,1000 if width>760 else 900,width<=760)
                cdp.navigate(base)
                cdp.evaluate("Promise.all([...document.querySelectorAll('.world-encounter img')].map(img=>img.decode())).then(()=>true)")
                cdp.evaluate("scrollTo({top:0,behavior:'instant'})")
                time.sleep(.07)
                read_space = """(()=>{
                  const saturn=document.querySelector('.world-saturn'),pluto=document.querySelector('.world-pluto'),r=pluto.getBoundingClientRect();
                  return {saturn:Number(getComputedStyle(saturn).opacity),pluto:Number(getComputedStyle(pluto).opacity),saturnLeft:saturn.getBoundingClientRect().left,plutoVisible:(Math.min(innerWidth,r.right)-Math.max(0,r.left))/r.width,galaxy:new DOMMatrix(getComputedStyle(document.querySelector('.milky-way')).transform).m42,near:new DOMMatrix(getComputedStyle(document.querySelector('.stars-near')).transform).m42,far:new DOMMatrix(getComputedStyle(document.querySelector('.stars-far')).transform).m42,overflow:document.documentElement.scrollWidth>innerWidth};
                })()"""
                initial = cdp.evaluate(read_space)
                check(initial['saturn']==0 and initial['pluto']==0, f'Large planet encounters wait until scrolling starts at {width}px')
                check(cdp.evaluate("[...document.querySelectorAll('.world-encounter img')].every(img=>img.complete&&img.naturalWidth>0)"), f'All four planet photographs load at {width}px')
                check(cdp.evaluate("!document.querySelector('.space-debris .stack-logo')"), f'Asteroids are plain rocks again at {width}px')
                craft_state = "[...document.querySelectorAll('.spacecraft')].filter(e=>getComputedStyle(e).display!=='none').map(e=>getComputedStyle(e).transform)"
                craft_before = cdp.evaluate(craft_state)
                time.sleep(.18)
                check(cdp.evaluate(craft_state)!=craft_before, f'Spacecraft drift with decorative motion enabled at {width}px')
                check(cdp.evaluate("[...document.querySelectorAll('.craft-satellite .craft-flame')].length===0 && [...document.querySelectorAll('.craft-rocket,.craft-ufo')].every(e=>e.querySelector('.craft-flame'))"), f'Exhaust follows rockets and UFOs while satellites have none at {width}px')
                check(len(craft_before)==(6 if width<=760 else 12), f'Spacecraft density adapts to the viewport at {width}px')
                cdp.evaluate("scrollTo({top:(document.documentElement.scrollHeight-innerHeight)*.22,behavior:'instant'})")
                time.sleep(.65)
                first = cdp.evaluate(read_space)
                check(first['saturn']>.18 and first['pluto']==0 and first['saturnLeft']<0, f'Cropped Saturn appears first on the left at {width}px')
                check(first['galaxy']<0 and first['near']<first['far']<0, f'Galaxy and stars travel at different depths at {width}px')
                cdp.screenshot(f'universe-saturn-{width}.png')
                cdp.evaluate("scrollTo({top:(document.documentElement.scrollHeight-innerHeight)*.44,behavior:'instant'})")
                time.sleep(.65)
                earth = cdp.evaluate("(()=>{const e=document.querySelector('.world-earth'),r=e.getBoundingClientRect();return {opacity:Number(getComputedStyle(e).opacity),center:r.left+r.width/2,expected:document.documentElement.clientWidth/2}})()")
                check(earth['opacity']>.1 and abs(earth['center']-earth['expected'])<1, f'Earth appears in the center after Saturn at {width}px')
                cdp.screenshot(f'universe-earth-{width}.png')
                cdp.evaluate("scrollTo({top:(document.documentElement.scrollHeight-innerHeight)*.62,behavior:'instant'})")
                time.sleep(.65)
                check(cdp.evaluate("Number(getComputedStyle(document.querySelector('.world-mars')).opacity)>.15 && document.querySelector('.world-mars').getBoundingClientRect().left<0 && Number(getComputedStyle(document.querySelector('.world-earth')).opacity)===0"), f'Mars appears next at the left edge at {width}px')
                cdp.screenshot(f'universe-mars-{width}.png')
                cdp.evaluate("scrollTo({top:(document.documentElement.scrollHeight-innerHeight)*.76,behavior:'instant'})")
                time.sleep(.65)
                second = cdp.evaluate(read_space)
                check(second['saturn']==0 and second['pluto']>.15 and .5<second['plutoVisible']<1, f'More than half of Pluto appears later on the right at {width}px')
                check(not first['overflow'] and not second['overflow'], f'Cropped planets introduce no horizontal overflow at {width}px')
                cdp.screenshot(f'universe-pluto-{width}.png')
                cdp.evaluate("scrollTo({top:(document.documentElement.scrollHeight-innerHeight)*.22,behavior:'instant'})")
                time.sleep(.1)
                check(cdp.evaluate(read_space)['saturn']>.18, f'Scrolling back restores the earlier Saturn encounter at {width}px')
                cdp.evaluate("document.querySelector('.motion-toggle').click()")
                frozen = cdp.evaluate(read_space)
                craft_frozen = cdp.evaluate(craft_state)
                cdp.evaluate("scrollTo({top:(document.documentElement.scrollHeight-innerHeight)*.76,behavior:'instant'})")
                time.sleep(.1)
                check(cdp.evaluate(read_space)['galaxy']==frozen['galaxy'], f'Pause control freezes universe travel at {width}px')
                check(cdp.evaluate(craft_state)==craft_frozen and cdp.evaluate("[...document.querySelectorAll('.spacecraft,.craft-flame')].every(e=>getComputedStyle(e).animationPlayState==='paused')"), f'Pause control freezes spacecraft and exhaust at {width}px')
                cdp.evaluate("document.querySelector('.motion-toggle').click()")
                cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
                time.sleep(.06)
                reduced = cdp.evaluate(read_space)
                check(reduced['galaxy']==0 and reduced['near']==0 and reduced['far']==0, f'Reduced motion disables all background parallax at {width}px')
                check(cdp.evaluate("[...document.querySelectorAll('.spacecraft')].every(e=>getComputedStyle(e).animationName==='none') && [...document.querySelectorAll('.craft-flame')].every(e=>getComputedStyle(e).display==='none')"), f'Reduced motion stops craft and hides exhaust at {width}px')
                cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]})
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})

            # The reference-inspired sections remain usable across screen sizes.
            for width in (1440,768,390,320):
                cdp.viewport(width,1000 if width>760 else 900,width<=760)
                cdp.navigate(base)
                check(cdp.evaluate("[...document.querySelectorAll('.career-card,.academic-row,.proficiency-row,.contact-layout')].every(e=>e.scrollWidth<=e.clientWidth+1)"), f'New section content fits its layout at {width}px')
                for section_id in ('what-i-do','proficiency','experience','education','contact'):
                    cdp.evaluate(f"document.getElementById('{section_id}').scrollIntoView({{behavior:'instant'}})")
                    time.sleep(.1)
                    if section_id=='contact':
                        check(cdp.evaluate("document.querySelector('.portrait-frame img').decode().then(()=>document.querySelector('.portrait-frame img').naturalWidth>0)"), f'The supplied contact portrait loads at {width}px')
                    if width in (1440,390): cdp.screenshot(f'section-{section_id}-{width}.png')
                check(cdp.evaluate("document.documentElement.scrollWidth<=innerWidth"), f'Illustrations, cards, and portrait create no horizontal overflow at {width}px')

            cdp.viewport(1440)
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]})
            cdp.navigate(base)
            cdp.evaluate("document.getElementById('what-i-do').scrollIntoView({behavior:'instant'})")
            time.sleep(.7)
            gear_before=cdp.evaluate("getComputedStyle(document.querySelector('.illustration-gear')).transform")
            time.sleep(.25)
            check(cdp.evaluate("getComputedStyle(document.querySelector('.illustration-gear')).transform")!=gear_before, 'The overview illustration animates while visible')
            cdp.evaluate("document.querySelector('.motion-toggle').click()")
            check(cdp.evaluate("getComputedStyle(document.querySelector('.illustration-gear')).animationPlayState==='paused'"), 'The motion control pauses the new illustrations')
            cdp.evaluate("document.querySelector('.motion-toggle').click();document.getElementById('proficiency').scrollIntoView({behavior:'instant'})")
            time.sleep(1.1)
            check(cdp.evaluate("[...document.querySelectorAll('.proficiency-row')].filter(e=>{const r=e.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0}).every(e=>!e.classList.contains('is-waiting')&&getComputedStyle(e.querySelector('.proficiency-tools')).clipPath.includes('0px'))"), 'Proficiency tool bars reveal when scrolled into view')
            cdp.evaluate("scrollTo({top:0,behavior:'instant'})")
            time.sleep(.1)
            check(cdp.evaluate("document.querySelector('.work-art').classList.contains('is-offscreen') && getComputedStyle(document.querySelector('.illustration-gear')).animationPlayState==='paused'"), 'Offscreen illustrations stop animating')
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
            time.sleep(.06)
            check(cdp.evaluate("getComputedStyle(document.querySelector('.illustration-gear')).animationName==='none' && [...document.querySelectorAll('.proficiency-tools')].every(e=>getComputedStyle(e).clipPath==='none')"), 'Reduced motion disables illustration motion and shows tool bars immediately')

            # All planets are real anchors; native click and history remain usable.
            cdp.viewport(1440)
            cdp.navigate(base)
            for kind, target in [('origin','about'),('career','experience'),('project','projects'),('tech','skills'),('academic','education'),('signal','contact')]:
                cdp.evaluate(f"document.querySelector('.planet-{kind}').click()")
                check(cdp.evaluate('location.hash') == '#'+target, f'{kind} planet navigates to {target}')
                position = cdp.evaluate(f"document.getElementById('{target}').querySelector('.section-index').getBoundingClientRect().top")
                check(position >= 70, f'{target} content clears the sticky header')

            cdp.navigate(base)
            cdp.evaluate("document.getElementById('projects').scrollIntoView({behavior:'instant'})")
            time.sleep(.2)
            check(cdp.evaluate("document.querySelector('.desktop-nav a[data-section=projects]').getAttribute('aria-current')") == 'location', 'Active navigation follows the visible section')
            cdp.screenshot('projects-desktop.png')
            cdp.evaluate("document.querySelector('.project-link').click()")
            time.sleep(.3)
            check(cdp.evaluate('location.pathname') == '/projects/data-man.html', 'Project card opens its real case-study page')
            cdp.evaluate('history.back()')
            time.sleep(.3)
            check(cdp.evaluate('location.pathname') == '/', 'Native browser Back returns from a case study')

            for slug in ('data-man','kira','patent-search','inference-routing'):
                cdp.navigate(base+'/projects/'+slug+'.html')
                check(cdp.evaluate("document.querySelectorAll('.case-content section').length") == 6, f'{slug} case study has all six substantive sections')
                check(cdp.evaluate("document.querySelector('.case-back').href.endsWith('index.html#projects')"), f'{slug} returns to project showcase')
                cdp.viewport(320,900,True)
                check(cdp.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'{slug} case study fits 320px')
                cdp.viewport(1440)
                if slug == 'data-man':
                    cdp.screenshot('case-study-desktop.png')

            # Mobile disclosure: keyboard activation, Escape, and touch activation.
            cdp.viewport(390,900,True)
            cdp.navigate(base)
            cdp.call('Page.bringToFront')
            cdp.evaluate("document.querySelector('.menu-toggle').focus()")
            for event_type in ('keyDown','keyUp'):
                cdp.call('Input.dispatchKeyEvent',{'type':event_type,'key':'Enter','code':'Enter','windowsVirtualKeyCode':13,'nativeVirtualKeyCode':13,**({'text':'\r','unmodifiedText':'\r'} if event_type == 'keyDown' else {})})
            check(cdp.evaluate("document.querySelector('.menu-toggle').getAttribute('aria-expanded')") == 'true', 'Mobile menu opens with keyboard')
            cdp.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27})
            check(cdp.evaluate("document.getElementById('mobile-nav').hidden && document.activeElement.classList.contains('menu-toggle')"), 'Escape closes menu and restores focus')
            bounds = cdp.evaluate("(()=>{const r=document.querySelector('.menu-toggle').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
            cdp.call('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':bounds['x'],'y':bounds['y']}]})
            cdp.call('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            time.sleep(.2)
            check(cdp.evaluate("document.querySelector('.menu-toggle').getAttribute('aria-expanded')") == 'true', 'Mobile menu opens with touch')
            cdp.evaluate("document.querySelector('#mobile-nav [data-section=projects]').click()")
            check(cdp.evaluate("location.hash === '#projects' && document.getElementById('mobile-nav').hidden"), 'Mobile section navigation closes menu')
            check(cdp.evaluate("document.activeElement.id") == 'projects', 'Mobile navigation transfers focus to the destination')

            cdp.navigate(base)
            cdp.evaluate("document.querySelector('.planet-project').scrollIntoView({block:'center'})")
            bounds = cdp.evaluate("(()=>{const r=document.querySelector('.planet-project .planet-sphere').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
            cdp.call('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[bounds]})
            cdp.call('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            time.sleep(.2)
            check(cdp.evaluate('location.hash') == '#projects', 'Planet navigation responds to a real touch event')

            # Keyboard focus is visible on the actual planetary anchors.
            cdp.viewport(1440)
            cdp.call('Emulation.setTouchEmulationEnabled',{'enabled':False})
            cdp.navigate(base)
            cdp.evaluate("document.querySelector('.planet-project').focus()")
            check(cdp.evaluate("document.activeElement.classList.contains('planet-project') && getComputedStyle(document.activeElement).outlineStyle !== 'none'"), 'Planet keyboard focus has a visible outline')
            check(cdp.evaluate("getComputedStyle(document.querySelector('.planet-project .planet-tooltip')).visibility") == 'visible', 'Planet description is available on keyboard focus')

            cdp.evaluate("document.querySelector('[data-skill=Python]').focus()")
            check('Backend services' in cdp.evaluate("document.getElementById('skill-description').textContent"), 'Skill node focus reveals contextual information')
            cdp.evaluate("document.querySelector('[data-node=kv-cache]').focus()")
            check('attention keys and values' in cdp.evaluate("document.getElementById('skill-description').textContent"), 'KV-Cache node reveals its inference context')
            check(cdp.evaluate("document.querySelector('.constellation-map line.is-active[data-to=\"kv-cache\"]') !== null && document.querySelector('[data-node=kv-cache]').getAttribute('aria-pressed') === 'true'"), 'Selected skill highlights its network connections')

            check(cdp.evaluate("[...document.querySelectorAll('.constellation-node')].every(e=>e.querySelector('svg.stack-logo')&&e.getAttribute('aria-label')===e.dataset.skill)"), 'Every skill has an icon and accessible name')
            check(cdp.evaluate("getComputedStyle(document.querySelector('[data-node=kv-cache] .skill-tooltip')).visibility==='visible'"), 'Keyboard focus reveals the skill name tooltip')
            cdp.evaluate("document.activeElement.blur();document.querySelector('[data-node=python]').scrollIntoView({block:'center',behavior:'instant'})")
            pos=cdp.evaluate("(()=>{const r=document.querySelector('[data-node=python]').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()")
            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved',**pos})
            time.sleep(.2)
            check(cdp.evaluate("getComputedStyle(document.querySelector('[data-node=python] .skill-tooltip')).visibility==='visible' && document.querySelector('[data-node=python] .skill-tooltip').textContent==='Python'"), 'Hovering a logo reveals its skill name')
            check(cdp.evaluate("document.querySelector('[data-node=python]').getAttribute('aria-pressed')==='true' && document.querySelector('[data-node=kv-cache]').getAttribute('aria-pressed')==='false' && document.getElementById('skill-description').textContent.startsWith('Python')"), 'Mouse hover updates the selected skill and clears the previous tooltip on hybrid devices')
            cdp.screenshot('skills-logo-tooltip-1440.png')
            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':5,'y':130})
            time.sleep(.2)
            check(cdp.evaluate("getComputedStyle(document.querySelector('[data-node=python] .skill-tooltip')).visibility==='hidden'"), 'Skill tooltip hides when the pointer leaves')
            cdp.viewport(390,900,True)
            cdp.call('Emulation.setTouchEmulationEnabled',{'enabled':True})
            cdp.navigate(base)
            cdp.evaluate("document.querySelector('.constellation').scrollIntoView({block:'center',behavior:'instant'})")
            pos=cdp.evaluate("(()=>{const r=document.querySelector('[data-node=python]').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()")
            cdp.call('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[pos]})
            cdp.call('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            time.sleep(.2)
            check(cdp.evaluate("document.querySelector('[data-node=python]').getAttribute('aria-pressed')==='true' && getComputedStyle(document.querySelector('[data-node=python] .skill-tooltip')).visibility==='visible'"), 'Tapping a skill icon reveals its name on mobile')
            cdp.screenshot('skills-logo-tooltip-390.png')
            cdp.call('Emulation.setTouchEmulationEnabled',{'enabled':False})
            check(cdp.evaluate("document.querySelector('.footer-signature').textContent==='made by murtaza with ❤️' && !document.querySelector('.image-credit')"), 'Footer shows the requested personal signature')

            # User control of animation, independent of system preference.
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]})
            cdp.viewport(1440)
            cdp.navigate(base)
            time.sleep(1)
            check(cdp.evaluate("!document.querySelector('.motion-toggle').hidden && getComputedStyle(document.querySelector('.planet-sphere')).animationName !== 'none'"), 'Decorative motion is enabled when permitted')
            sample_motion = "({position:document.querySelector('.planet-project').style.translate,surface:getComputedStyle(document.querySelector('.planet-project .planet-sphere'),'::before').backgroundPosition,stars:[...document.querySelectorAll('.sparkle')].map(e=>getComputedStyle(e).opacity)})"
            before = cdp.evaluate(sample_motion)
            time.sleep(.65)
            after = cdp.evaluate(sample_motion)
            check(before['position'] != after['position'], 'Planets visibly advance along their orbital paths')
            check(before['surface'] != after['surface'], 'Planet surface textures rotate independently')
            check(before['stars'] != after['stars'], 'Stars sparkle with independently timed brightness')
            bounds = cdp.evaluate("(()=>{const r=document.querySelector('.solar-scene').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved',**bounds})
            time.sleep(.06)
            before = cdp.evaluate(sample_motion)
            time.sleep(.2)
            after = cdp.evaluate(sample_motion)
            check(before['position'] == after['position'] and before['surface'] == after['surface'], 'Pointer approach pauses orbit and surface rotation')
            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':0,'y':0})
            cdp.evaluate("document.querySelector('.motion-toggle').click()")
            check(cdp.evaluate("document.documentElement.dataset.motion === 'paused' && document.querySelector('.motion-toggle').getAttribute('aria-pressed') === 'true'"), 'Pause control stops decorative motion')
            time.sleep(.06)
            before = cdp.evaluate(sample_motion)
            time.sleep(.2)
            after = cdp.evaluate(sample_motion)
            check(before == after, 'Pause control freezes orbital motion, rotation, and sparkles')
            cdp.navigate(base)
            check(cdp.evaluate("document.documentElement.dataset.motion") == 'paused', 'Motion preference persists across page loads')
            cdp.evaluate("document.querySelector('.motion-toggle').click()")
            cdp.evaluate("document.querySelector('.planet-project').focus()")
            check(cdp.evaluate("getComputedStyle(document.querySelector('.planet-project .planet-sphere')).animationPlayState") == 'paused', 'Planet motion stabilizes during keyboard focus')
            time.sleep(.06)
            before = cdp.evaluate(sample_motion)
            time.sleep(.2)
            after = cdp.evaluate(sample_motion)
            check(before['position'] == after['position'] and before['surface'] == after['surface'], 'Keyboard focus freezes the orbital navigation target')

            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':120,'y':450})
            time.sleep(.25)
            check(cdp.evaluate("(()=>{const g=document.querySelector('.cursor-glow'),m=new DOMMatrix(getComputedStyle(g).transform);return g.hasAttribute('data-active')&&getComputedStyle(g).pointerEvents==='none'&&m.m41===120&&m.m42===450&&Number(getComputedStyle(g).opacity)>.9})()"), 'Ambient light follows the cursor outside the solar scene without blocking interaction')
            check(cdp.evaluate("getComputedStyle(document.querySelector('.solar-scene'),'::after').content === 'none'"), 'Solar scene has no rectangular cursor-glow layer')
            bounds = cdp.evaluate("(()=>{const r=document.querySelector('.solar-scene').getBoundingClientRect();return {x:r.x+5,y:r.bottom-15}})()")
            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved',**bounds})
            time.sleep(.1)
            cdp.screenshot('cursor-glow-solar-edge.png')
            cdp.evaluate("document.getElementById('projects').scrollIntoView()")
            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':450,'y':600})
            time.sleep(.15)
            check(cdp.evaluate("(()=>{const g=document.querySelector('.cursor-glow'),m=new DOMMatrix(getComputedStyle(g).transform),r=g.parentElement.getBoundingClientRect();return g.hasAttribute('data-active')&&m.m41===450&&m.m42===600&&r.top===0&&r.height===innerHeight})()"), 'Cursor light stays aligned to the viewport after scrolling')
            cdp.screenshot('cursor-glow-projects.png')
            cdp.navigate(base+'/projects/data-man.html')
            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':300,'y':450})
            time.sleep(.25)
            check(cdp.evaluate("document.querySelector('.cursor-glow').hasAttribute('data-active')"), 'Page-wide cursor light also works on case studies')
            cdp.call('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':300,'y':450}]})
            cdp.call('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            check(cdp.evaluate("!document.querySelector('.cursor-glow').hasAttribute('data-active')"), 'Touch input clears cursor decoration')
            cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':350,'y':450})
            time.sleep(.06)
            cdp.evaluate("document.dispatchEvent(new PointerEvent('pointerleave'))")
            check(cdp.evaluate("!document.querySelector('.cursor-glow').hasAttribute('data-active')"), 'Cursor light clears when the pointer leaves the page')
            cdp.navigate(base)

            # Project previews animate on actual mouse hover, with no idle loop.
            cdp.call('Emulation.setTouchEmulationEnabled',{'enabled':False})
            for slug, selector, property_name in [
                ('data-man','.chart-bars i','transform'),
                ('kira','.agent-core','scale'),
                ('patent-search','.search-lens','translate'),
                ('inference-routing','.routing-packet-in','strokeDashoffset')
            ]:
                card = f"document.querySelector('.art-{slug}').closest('.project-card')"
                cdp.evaluate(f"{card}.scrollIntoView({{behavior:'instant',block:'center'}})")
                bounds = cdp.evaluate(f"(()=>{{const r={card}.querySelector('.project-art').getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
                cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved',**bounds})
                time.sleep(.1)
                target = f"{card}.querySelector('{selector}')"
                hover_state = cdp.evaluate(f"({{hovered:{card}.matches(':hover'),animation:getComputedStyle({target}).animationName,canHover:matchMedia('(hover:hover)').matches,focus:document.activeElement.className}})")
                check(hover_state['hovered'] and hover_state['animation'] != 'none', f'{slug} illustration animates on mouse hover: {hover_state}')
                before = cdp.evaluate(f"getComputedStyle({target}).{property_name}")
                time.sleep(.25)
                after = cdp.evaluate(f"getComputedStyle({target}).{property_name}")
                check(before != after, f'{slug} hover produces visible animation')
                cdp.screenshot(f'project-hover-{slug}.png')
                if slug == 'inference-routing':
                    stages = cdp.evaluate("""(()=>{
                      const art=document.querySelector('.art-inference-routing');
                      const animations=art.getAnimations({subtree:true}).filter(a=>a.animationName?.startsWith('routing-'));
                      const read=time=>{
                        animations.forEach(a=>{a.pause();a.currentTime=time});
                        return {incoming:Number(getComputedStyle(art.querySelector('.routing-packet-in')).opacity),outgoing:Number(getComputedStyle(art.querySelector('.routing-packet-out')).opacity),thinking:Number(getComputedStyle(art.querySelector('.routing-thinking i')).opacity),selected:Number(art.dataset.routingTarget)-1,tiers:[...art.querySelectorAll('.gpu-stack>span')].map(e=>getComputedStyle(e).backgroundColor)};
                      };
                      return [read(160),read(560),read(960),read(1320)];
                    })()""")
                    check(stages[0]['incoming'] > .9 and stages[0]['thinking'] == 0 and stages[0]['outgoing'] == 0, 'Request reaches the placement layer before routing begins')
                    check(stages[1]['incoming'] == 0 and stages[1]['thinking'] > .25 and stages[1]['outgoing'] == 0, 'Placement layer briefly evaluates the route')
                    check(stages[2]['outgoing'] > .9 and stages[2]['thinking'] == 0, 'Request travels down its selected GPU branch')
                    selected = stages[3]['selected']
                    idle_tiers = [color for index,color in enumerate(stages[3]['tiers']) if index != selected]
                    check(idle_tiers[0] == idle_tiers[1] and stages[3]['tiers'][selected] != idle_tiers[0], 'Only the randomly selected GPU confirms the routing decision')
                    check(cdp.evaluate("getComputedStyle(document.querySelector('.routing-packet-in')).animationDuration") == '1.6s', 'Complete request-routing sequence takes 1.6 seconds')
                    routes = cdp.evaluate("""(()=>{
                      const art=document.querySelector('.art-inference-routing'),random=Math.random;
                      try {
                        return [0,.5,.999].map(value=>{
                          Math.random=()=>value;
                          art.querySelector('.routing-packet-in').dispatchEvent(new AnimationEvent('animationiteration',{animationName:'routing-arrival',bubbles:true}));
                          const selected=Number(art.dataset.routingTarget);
                          return {selected,highlight:[...art.querySelectorAll('.gpu-stack>span')].findIndex(e=>e.classList.contains('gpu-selected'))+1,count:art.querySelectorAll('.gpu-selected').length,pathMatches:art.querySelector('.routing-packet-out').getAttribute('d')===art.querySelector('.routing-wire-'+selected).getAttribute('d')};
                        });
                      } finally {Math.random=random}
                    })()""")
                    check([route['selected'] for route in routes] == [1,2,3], 'Every GPU can be selected on a new request cycle')
                    check(all(route['selected'] == route['highlight'] and route['count'] == 1 and route['pathMatches'] for route in routes), 'Random routing keeps the packet path and single GPU highlight synchronized')
                    cdp.evaluate("document.querySelector('.art-inference-routing').getAnimations({subtree:true}).filter(a=>a.animationName?.startsWith('routing-')).forEach(a=>{a.pause();a.currentTime=1320})")
                    cdp.screenshot('project-routing-random.png')
                cdp.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':0,'y':0})
                time.sleep(.06)
                check(cdp.evaluate(f"getComputedStyle({target}).animationName") == 'none', f'{slug} animation stops after pointer exit')

            cdp.evaluate("document.querySelector('.project-link').focus()")
            check(cdp.evaluate("getComputedStyle(document.querySelector('.chart-bars i')).animationName") == 'project-chart', 'Keyboard focus activates project illustration motion')
            cdp.evaluate("document.querySelector('.motion-toggle').click()")
            check(cdp.evaluate("getComputedStyle(document.querySelector('.chart-bars i')).animationPlayState") == 'paused', 'Motion control pauses focused project animations')
            cdp.evaluate("document.querySelector('.motion-toggle').click()")
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
            check(cdp.evaluate("[...document.querySelectorAll('.project-art *')].every(e=>getComputedStyle(e).animationName==='none') && getComputedStyle(document.querySelector('.doc-front'),'::after').animationName==='none'"), 'Reduced motion disables all project preview animations')
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]})
            cdp.navigate(base)

            # Animation lifecycle: hidden pages and scenes out of view pause.
            cdp.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
            check(cdp.evaluate("document.documentElement.hasAttribute('data-page-hidden') && getComputedStyle(document.querySelector('.stars-near')).animationPlayState === 'paused'"), 'Hidden-page lifecycle pauses decorative animation')
            cdp.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));document.activeElement.blur();document.getElementById('contact').scrollIntoView()")
            time.sleep(.8)
            check(cdp.evaluate("document.querySelector('.solar').classList.contains('is-offscreen')"), 'Offscreen solar animation is suspended')

            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
            cdp.navigate(base)
            check(cdp.evaluate("getComputedStyle(document.querySelector('.cursor-glow')).display === 'none'"), 'Reduced motion disables the page-wide cursor effect')
            check(cdp.evaluate("document.querySelector('.contact-links a').href === 'https://www.linkedin.com/in/murtazaverse'"), 'LinkedIn destination matches verified profile')
            check(cdp.evaluate("document.querySelector('.contact-links a:nth-child(2)').href === 'https://github.com/murtazaverse'"), 'GitHub destination matches verified profile')
            check(cdp.evaluate("document.querySelector('.email-link').href === 'mailto:murtazazaidi.tech@gmail.com'"), 'Email destination matches verified profile')
            pdf = wait_http(cdp.evaluate("document.querySelector('#resume a[download]').href"))
            check(pdf.startswith(b'%PDF'), 'Résumé action serves a real PDF')
            check(cdp.evaluate("document.querySelector('#resume a[download]').getAttribute('href') === 'assets/documents/resume.pdf' && document.querySelector('#resume a[download]').download === 'MURTAZA_ZAIDI_RESUME.pdf' && !document.querySelector('#resume').textContent.includes('previous')"), 'Latest document-folder résumé is linked with the current download filename')
            check(cdp.evaluate("document.querySelectorAll('canvas').length === 0"), 'All functionality runs with WebGL disabled')
            ax = cdp.call('Accessibility.getFullAXTree')['nodes']
            unnamed = [node for node in ax if not node.get('ignored') and node.get('role',{}).get('value') in ('button','link') and not node.get('name',{}).get('value','').strip()]
            check(not unnamed, 'Every exposed link and button has an accessible name')

            for width in (1440,390):
                cdp.viewport(width,1000 if width>760 else 900,width<=760)
                cdp.navigate(base)
                for section in ('experience','skills','education','contact'):
                    cdp.evaluate(f"document.getElementById('{section}').scrollIntoView()")
                    time.sleep(.12)
                    cdp.screenshot(f'{section}-{width}.png')

            # Progressive baseline: no script required to read or navigate the site.
            cdp.call('Emulation.setScriptExecutionDisabled',{'value':True})
            cdp.navigate(base)
            check(cdp.evaluate("document.querySelector('h1').getBoundingClientRect().height > 0"), 'Professional introduction is visible without JavaScript')
            check(cdp.evaluate("document.querySelectorAll('.nojs-nav a').length === 7 && document.querySelector('.nojs-nav').getBoundingClientRect().height > 0"), 'Conventional mobile navigation works without JavaScript')
            check(cdp.evaluate("[...document.querySelectorAll('.project-card')].every(e=>getComputedStyle(e).opacity === '1')"), 'All project content remains visible without JavaScript')
            cdp.call('Emulation.setScriptExecutionDisabled',{'value':False})
            cdp.navigate(base)

            report['console_errors'] = [x for x in cdp.events if x.get('method') == 'Runtime.exceptionThrown' or (x.get('method') == 'Runtime.consoleAPICalled' and x.get('params',{}).get('type')=='error')]
            report['failed_requests'] = [x['params'] for x in cdp.events if x.get('method') == 'Network.loadingFailed' and not x.get('params',{}).get('canceled')]
            report['http_errors'] = [{'url':x['params']['response']['url'],'status':x['params']['response']['status']} for x in cdp.events if x.get('method')=='Network.responseReceived' and x['params']['response']['status']>=400]
            check(not report['console_errors'], 'No runtime or console errors')
            check(not report['failed_requests'], 'No failed network requests')
            check(not report['http_errors'], 'No HTTP errors in the current site')
            cdp.call('Browser.close')
            processes[0].wait(timeout=10)
            cdp.socket.close()
        finally:
            (ARTIFACTS/'browser-report.json').write_text(json.dumps(report,indent=2))
            if processes and processes[0].poll() is None and 'cdp' in locals():
                try:
                    cdp.call('Browser.close')
                    processes[0].wait(timeout=10)
                except (ConnectionError, OSError, RuntimeError, subprocess.TimeoutExpired):
                    pass
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            log.close()
    print(f'Validated {len(report["checks"])} browser checks. Screenshots → artifacts/',flush=True)


if __name__ == '__main__':
    run()
