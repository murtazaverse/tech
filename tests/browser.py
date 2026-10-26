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
                network = cdp.evaluate("""(()=>{
                  const map=document.querySelector('.constellation-map').getBoundingClientRect();
                  const nodes=[...document.querySelectorAll('.constellation-node')].map(e=>({name:e.dataset.skill,rect:e.getBoundingClientRect()}));
                  const clipped=nodes.filter(n=>n.rect.left<map.left-1||n.rect.right>map.right+1||n.rect.top<map.top-1||n.rect.bottom>map.bottom+1).map(n=>n.name);
                  const overlapping=[];
                  nodes.forEach((a,i)=>nodes.slice(i+1).forEach(b=>{if(Math.min(a.rect.right,b.rect.right)-Math.max(a.rect.left,b.rect.left)>1&&Math.min(a.rect.bottom,b.rect.bottom)-Math.max(a.rect.top,b.rect.top)>1)overlapping.push([a.name,b.name])}));
                  return {clipped,overlapping};
                })()""")
                check(not network['clipped'] and not network['overlapping'], f'Skill network labels fit without overlap at {width}px: {network}')
                report['viewports'].append(measurements)
                cdp.screenshot(f'home-{width}.png')
                if width == 1440:
                    report['local_performance'] = cdp.evaluate("({vitals:window.__localVitals,resources:performance.getEntriesByType('resource').map(e=>({name:e.name.split('/').pop(),bytes:e.encodedBodySize,duration:e.duration}))})")
                    cdp.evaluate("document.querySelectorAll('.is-waiting').forEach(e=>e.classList.remove('is-waiting'))")
                    cdp.screenshot('desktop-full.png',True)
                if width == 390:
                    cdp.screenshot('mobile-full.png',True)

            # All planets are real anchors; native click and history remain usable.
            cdp.viewport(1440)
            cdp.navigate(base)
            for kind, target in [('origin','about'),('career','experience'),('project','projects'),('tech','skills'),('academic','education'),('signal','contact')]:
                cdp.evaluate(f"document.querySelector('.planet-{kind}').click()")
                check(cdp.evaluate('location.hash') == '#'+target, f'{kind} planet navigates to {target}')
                position = cdp.evaluate(f"document.getElementById('{target}').getBoundingClientRect().top")
                check(position >= 70, f'{target} destination clears the sticky header')

            cdp.navigate(base)
            cdp.evaluate("document.getElementById('projects').scrollIntoView()")
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
            cdp.navigate(base)
            cdp.evaluate("document.querySelector('.planet-project').focus()")
            check(cdp.evaluate("document.activeElement.classList.contains('planet-project') && getComputedStyle(document.activeElement).outlineStyle !== 'none'"), 'Planet keyboard focus has a visible outline')
            check(cdp.evaluate("getComputedStyle(document.querySelector('.planet-project .planet-tooltip')).visibility") == 'visible', 'Planet description is available on keyboard focus')

            cdp.evaluate("document.querySelector('[data-skill=Python]').focus()")
            check('Backend services' in cdp.evaluate("document.getElementById('skill-description').textContent"), 'Skill node focus reveals contextual information')
            cdp.evaluate("document.querySelector('[data-node=kv-cache]').focus()")
            check('attention keys and values' in cdp.evaluate("document.getElementById('skill-description').textContent"), 'KV-Cache node reveals its inference context')
            check(cdp.evaluate("document.querySelector('.constellation-map line.is-active[data-to=\"kv-cache\"]') !== null && document.querySelector('[data-node=kv-cache]').getAttribute('aria-pressed') === 'true'"), 'Selected skill highlights its network connections')

            # User control of animation, independent of system preference.
            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]})
            cdp.navigate(base)
            time.sleep(1)
            check(cdp.evaluate("!document.querySelector('.motion-toggle').hidden && getComputedStyle(document.querySelector('.planet-sphere')).animationName !== 'none'"), 'Decorative motion is enabled when permitted')
            cdp.evaluate("document.querySelector('.motion-toggle').click()")
            check(cdp.evaluate("document.documentElement.dataset.motion === 'paused' && document.querySelector('.motion-toggle').getAttribute('aria-pressed') === 'true'"), 'Pause control stops decorative motion')
            cdp.navigate(base)
            check(cdp.evaluate("document.documentElement.dataset.motion") == 'paused', 'Motion preference persists across page loads')
            cdp.evaluate("document.querySelector('.motion-toggle').click()")
            cdp.evaluate("document.querySelector('.planet-project').focus()")
            check(cdp.evaluate("getComputedStyle(document.querySelector('.planet-project .planet-sphere')).animationPlayState") == 'paused', 'Planet motion stabilizes during keyboard focus')

            # Animation lifecycle: hidden pages and scenes out of view pause.
            cdp.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
            check(cdp.evaluate("document.documentElement.hasAttribute('data-page-hidden') && getComputedStyle(document.querySelector('.stars-near')).animationPlayState === 'paused'"), 'Hidden-page lifecycle pauses decorative animation')
            cdp.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));document.activeElement.blur();document.getElementById('contact').scrollIntoView()")
            time.sleep(.8)
            check(cdp.evaluate("document.querySelector('.solar').classList.contains('is-offscreen')"), 'Offscreen solar animation is suspended')

            cdp.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
            cdp.navigate(base)
            check(cdp.evaluate("document.querySelector('.contact-links a').href === 'https://www.linkedin.com/in/murtazaverse'"), 'LinkedIn destination matches verified profile')
            check(cdp.evaluate("document.querySelector('.contact-links a:nth-child(2)').href === 'https://github.com/murtazaverse'"), 'GitHub destination matches verified profile')
            check(cdp.evaluate("document.querySelector('.email-link').href === 'mailto:murtazazaidi.tech@gmail.com'"), 'Email destination matches verified profile')
            pdf = wait_http(base+'/assets/documents/previous-resume.pdf')
            check(pdf.startswith(b'%PDF'), 'Résumé action serves a real PDF')
            check(cdp.evaluate("document.querySelector('#resume a[download]').textContent.includes('previous')"), 'Earlier résumé version is clearly identified')
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
            check(cdp.evaluate("document.querySelectorAll('.nojs-nav a').length === 6 && document.querySelector('.nojs-nav').getBoundingClientRect().height > 0"), 'Conventional mobile navigation works without JavaScript')
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
