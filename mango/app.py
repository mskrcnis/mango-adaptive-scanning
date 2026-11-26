"""Local offline replay and manual single-channel scanner interface."""
import json
import math
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import joblib
import numpy as np
import torch

from .models import partial_predict, controller_outputs
from .state import ROOT, atomic_json, digest
from .training import simulate


def load_runtime(folder=None):
    folder = ROOT / 'results/frozen' if folder is None else Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest.get('status') != 'frozen':
        raise RuntimeError('The scanner needs a verified frozen deployment bundle.')
    selection = json.loads((folder / 'selection.json').read_text())
    rule = selection['primary_rule']
    required = ['selection.json', 'experiment.json', 'catalog.json', 'demo_example.json', rule + '_seed42.joblib']
    for name in required:
        path = folder / name
        expected = manifest['hashes'].get(str(path.relative_to(ROOT)))
        if expected is None or digest(path) != expected:
            raise RuntimeError('Frozen deployment checksum mismatch: ' + name)
    configuration = json.loads((folder / 'experiment.json').read_text())
    index = selection['scientific_operating_indices'][rule + '|proposed']
    threshold = float(configuration['probability_threshold_grid'][index])
    bundle = joblib.load(folder / (rule + '_seed42.joblib'))
    torch.set_num_threads(int(bundle['config']['threads']))
    catalog = json.loads((folder / 'catalog.json').read_text())
    parts = [catalog[j] for j in bundle['bank_indices']]
    example = json.loads((folder / 'demo_example.json').read_text())
    return {'bundle': bundle, 'parts': parts, 'threshold': threshold, 'example': example,
            'rule': rule, 'operating_point': 'development-targeted primary scientific operating point',
            'manifest_sha256': digest(folder / 'manifest.json')}


class ReplaySource:
    def __init__(self, parts, readings):
        self._values = {part['id']: float(value) for part, value in zip(parts, readings)}
        self.requested = []

    def read_channel(self, led_id):
        if led_id in self.requested:
            raise ValueError('A channel has already been acquired')
        self.requested.append(led_id)
        return self._values[led_id]


class ManualInputSource:
    def read_channel(self, led_id):
        while True:
            value = input('Enter reference-normalized apparent absorbance for ' + led_id + ': ')
            try:
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError('nonfinite')
                return number
            except ValueError:
                print('Use one finite numeric reading.')


class ScannerSession:
    """Only add_reading receives a new measurement; no full spectrum is used."""
    def __init__(self, runtime, source=None):
        self.runtime = runtime
        self.bundle = runtime['bundle']
        self.parts = runtime['parts']
        self.threshold = runtime['threshold']
        self.source = source
        self.values = np.zeros(len(self.parts), dtype=np.float32)
        self.mask = np.zeros(len(self.parts), dtype=bool)
        self.trace = []
        self.started = time.perf_counter()

    @property
    def done(self):
        return bool(self.trace and self.trace[-1]['stop'])

    def requested_index(self):
        for j in self.bundle['initial_indices']:
            if not self.mask[j]:
                return int(j)
        return None if self.done else int(self.trace[-1]['next_channel'])

    def add_reading(self, led_id, reading):
        expected = self.requested_index()
        if expected is None:
            raise ValueError('This scan is complete')
        if led_id != self.parts[expected]['id']:
            raise ValueError('Supply only the requested LED: ' + self.parts[expected]['id'])
        try:
            value = float(reading)
        except (ValueError, TypeError):
            raise ValueError('The requested reading must be a finite number')
        if not math.isfinite(value) or abs(value) > np.finfo(np.float32).max:
            raise ValueError('The requested reading must be a finite float32 number')
        if self.mask[expected]:
            raise ValueError('A channel cannot be acquired twice')
        self.values[expected] = value
        self.mask[expected] = True
        if all(self.mask[j] for j in self.bundle['initial_indices']):
            prediction = partial_predict(self.bundle, self.values, self.mask)[0]
            probability, action = controller_outputs(self.bundle, self.values, self.mask)
            stop = bool(self.mask.all() or probability[0] <= self.threshold)
            next_channel = None if stop else int(np.argmax(action[0]))
            self.trace.append({'pulses': int(self.mask.sum()), 'mask': self.mask.astype(int).tolist(),
                               'readings': [float(self.values[j]) if self.mask[j] else None for j in range(len(self.mask))],
                               'prediction': float(prediction), 'p_stopgain': float(probability[0]),
                               'predicted_error': None, 'next_channel': next_channel, 'stop': stop})
        return self.snapshot()

    def start(self):
        if self.source is not None:
            while not all(self.mask[j] for j in self.bundle['initial_indices']):
                self.step()
        return self.snapshot()

    def step(self, reading=None, led_id=None):
        index = self.requested_index()
        if index is None:
            raise ValueError('This scan is complete')
        requested = self.parts[index]['id']
        if self.source is not None:
            if reading is not None or led_id is not None:
                raise ValueError('Replay measurements are supplied only by the replay source')
            reading = self.source.read_channel(requested)
        return self.add_reading(requested if led_id is None else led_id, reading)

    def snapshot(self):
        index = self.requested_index()
        final = self.trace[-1] if self.trace else {}
        return {'pulses': int(self.mask.sum()), 'capacity': len(self.parts), 'done': self.done,
                'prediction': final.get('prediction'), 'p_stopgain': final.get('p_stopgain'),
                'next_led': self.parts[index]['id'] if index is not None else None,
                'next_center_nm': self.parts[index]['center_nm'] if index is not None else None,
                'readings': [{'led_id': part['id'], 'center_nm': part['center_nm'],
                              'acquired': bool(self.mask[j]),
                              'value': float(self.values[j]) if self.mask[j] else None}
                             for j, part in enumerate(self.parts)],
                'trace': self.trace, 'threshold': self.threshold,
                'assay': None, 'assay_note': 'Laboratory assay is not included in this demo fixture.',
                'measurement_note': 'Simulated finite-band LED responses. Pulse counts represent simulated acquisition effort.'}

    def export(self):
        return {'schema_version': 1, 'method': 'proposed', 'rule': self.runtime['rule'],
                'threshold': self.threshold, 'operating_point': self.runtime['operating_point'],
                'frozen_manifest_sha256': self.runtime['manifest_sha256'],
                'example_row_id': self.runtime['example']['row_id'] if isinstance(self.source, ReplaySource) else None,
                'source': 'development replay' if isinstance(self.source, ReplaySource) else 'manual readings',
                'software_seconds': time.perf_counter() - self.started,
                'trace': self.trace, 'state': self.snapshot()}


def replay(manual=False, trace_output='results/demo_trace.json'):
    runtime = load_runtime()
    source = ManualInputSource() if manual else ReplaySource(runtime['parts'], runtime['example']['readings'])
    scanner = ScannerSession(runtime, source)
    print('Mango scanner: simulated LED readings; dry-matter estimates in percent fresh weight.')
    print('Operating point:', runtime['operating_point'], '| threshold:', runtime['threshold'])
    scanner.start()
    while True:
        state = scanner.snapshot()
        print('%d/%d pulses | dry matter %.3f%% | continuation probability %.3f | %s' %
              (state['pulses'], state['capacity'], state['prediction'], state['p_stopgain'],
               'STOP' if state['done'] else 'request ' + state['next_led']))
        if state['done']:
            break
        scanner.step()
    payload = scanner.export()
    destination = Path(trace_output)
    if not destination.is_absolute():
        destination = ROOT / destination
    atomic_json(destination, payload)
    print('Trace:', destination)
    print(state['assay_note'])
    return payload


HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mango scanner replay</title><style>
body{margin:0;background:#f5f4ec;color:#18352c;font:16px system-ui,sans-serif}main{max-width:980px;margin:auto;padding:36px 24px}
h1{font-size:36px;margin:8px 0}p{line-height:1.5}.eyebrow{color:#5e705c;letter-spacing:.12em;text-transform:uppercase;font-size:12px}
.panel{background:white;border:1px solid #d8ddcc;border-radius:14px;padding:24px;margin:20px 0}.stats{display:flex;gap:28px;flex-wrap:wrap}
.stat b{display:block;font-size:32px}.stat span{font-size:13px;color:#657469}button,a.button{background:#285b40;color:white;border:0;border-radius:8px;padding:12px 18px;font-size:15px;cursor:pointer;text-decoration:none;display:inline-block;margin-right:8px}
button:disabled{background:#a8b7ad;cursor:default}select,input{padding:10px;border:1px solid #bac8bc;border-radius:6px;font-size:15px}
.leds{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}.led{padding:8px 11px;border:1px solid #d8ddcc;border-radius:8px;background:#f5f6f0}.read{background:#e4efdb;border-color:#92ad73}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #e3e6dc}#error{color:#a52d25}small{color:#657469}#manual{display:none;margin:15px 0}
</style><main><div class="eyebrow">Offline spectral acquisition</div><h1>Mango scanner replay</h1>
<p>Reveal only the LED requested by the frozen scanner. Each reading updates the dry-matter estimate and the decision to continue.</p>
<div class="panel"><label>Reading source <select id="mode"><option value="replay">Real development example</option><option value="manual">Manual single-channel input</option></select></label>
<button onclick="start()">Start scan</button><p id="error"></p><div class="stats"><div class="stat"><b id="estimate">—</b><span>dry matter, % fresh weight</span></div><div class="stat"><b id="pulses">0 / 8</b><span>simulated LED pulses</span></div><div class="stat"><b id="decision">Ready</b><span id="next">start with two initial LEDs</span></div></div>
<div class="leds" id="leds"></div><div id="manual"><label>Requested LED reading <input id="reading" type="number" step="any" placeholder="apparent absorbance"></label></div>
<p><button id="step" onclick="step()" disabled>Acquire requested LED</button><a id="export" class="button" style="display:none">Export trace</a></p><small id="note">Simulated finite-band channels; this is a software demonstration.</small></div>
<div class="panel"><h2>Decision trace</h2><table><thead><tr><th>Pulses</th><th>Dry matter (%)</th><th>Continuation probability</th><th>Next action</th></tr></thead><tbody id="trace"></tbody></table></div>
<p><small>Pulse count is simulated acquisition effort. Energy, measurement noise, scan time and physical accuracy require a hardware experiment. The development fixture contains no assay value.</small></p></main>
<script>let session=null,state=null;async function call(url,obj){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});const p=await r.json();if(!r.ok)throw Error(p.error);return p}
function render(s){state=s;document.getElementById('estimate').textContent=s.prediction===null?'—':s.prediction.toFixed(3);document.getElementById('pulses').textContent=s.pulses+' / '+s.capacity;document.getElementById('decision').textContent=s.done?'Stopped':'Continue';document.getElementById('next').textContent=s.done?'final estimate':'request '+s.next_led+' ('+s.next_center_nm+' nm)';document.getElementById('step').disabled=s.done;document.getElementById('manual').style.display=document.getElementById('mode').value==='manual'&&!s.done?'block':'none';document.getElementById('leds').innerHTML=s.readings.map(r=>'<div class="led '+(r.acquired?'read':'')+'">'+r.center_nm+' nm<br><small>'+(r.acquired?r.value.toFixed(5):'unread')+'</small></div>').join('');document.getElementById('trace').innerHTML=s.trace.map(t=>'<tr><td>'+t.pulses+'</td><td>'+t.prediction.toFixed(3)+'</td><td>'+t.p_stopgain.toFixed(3)+'</td><td>'+(t.stop?'stop':s.readings[t.next_channel].led_id)+'</td></tr>').join('');document.getElementById('export').style.display='inline-block';document.getElementById('export').href='/api/export?session='+session;document.getElementById('note').textContent=s.measurement_note}
async function start(){try{document.getElementById('error').textContent='';let p=await call('/api/start',{mode:document.getElementById('mode').value});session=p.session;render(p.state)}catch(e){document.getElementById('error').textContent=e.message}}
async function step(){try{document.getElementById('error').textContent='';let p={session};if(document.getElementById('mode').value==='manual'){p.reading=document.getElementById('reading').value;p.led_id=state.next_led}render((await call('/api/step',p)).state);document.getElementById('reading').value=''}catch(e){document.getElementById('error').textContent=e.message}}</script></html>'''


def _make_server(runtime, port):
    sessions = {}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            return

        def send(self, code, payload, mime='application/json'):
            data = payload.encode() if isinstance(payload, str) else json.dumps(payload, allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            route = urlparse(self.path)
            if route.path == '/':
                return self.send(200, HTML, 'text/html')
            if route.path == '/api/export':
                key = parse_qs(route.query).get('session', [''])[0]
                with lock:
                    if key in sessions:
                        return self.send(200, sessions[key].export())
                return self.send(404, {'error': 'Unknown scanner session'})
            return self.send(404, {'error': 'Unknown endpoint'})

        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length > 4096:
                    raise ValueError('Request too large')
                payload = json.loads(self.rfile.read(length))
                with lock:
                    if self.path == '/api/start':
                        mode = payload.get('mode', 'replay')
                        if mode not in ['manual', 'replay']:
                            raise ValueError('Unknown reading source')
                        source = ReplaySource(runtime['parts'], runtime['example']['readings']) if mode == 'replay' else None
                        scanner = ScannerSession(runtime, source)
                        key = uuid.uuid4().hex
                        sessions[key] = scanner
                        return self.send(200, {'session': key, 'state': scanner.start()})
                    if self.path == '/api/step':
                        scanner = sessions.get(payload.get('session'))
                        if scanner is None:
                            raise ValueError('Unknown scanner session')
                        state = scanner.step(payload.get('reading'), payload.get('led_id'))
                        return self.send(200, {'state': state})
                    return self.send(404, {'error': 'Unknown endpoint'})
            except (ValueError, TypeError, KeyError) as exc:
                return self.send(400, {'error': str(exc)})

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def _http_test(runtime):
    server = _make_server(runtime, 0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = 'http://127.0.0.1:%d' % server.server_port
    checks = {}

    def post(path, data):
        request = Request(base + path, json.dumps(data).encode(), {'Content-Type': 'application/json'})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    try:
        with urlopen(base, timeout=30) as response:
            checks['html_route'] = response.status == 200 and b'Mango scanner replay' in response.read()
        start = post('/api/start', {'mode': 'replay'})
        session, state = start['session'], start['state']
        for _ in range(len(runtime['parts'])):
            if state['done']:
                break
            state = post('/api/step', {'session': session})['state']
        with urlopen(base + '/api/export?session=' + session, timeout=30) as response:
            exported = json.load(response)
        expected = simulate(runtime['bundle'], runtime['example']['readings'], 'proposed', runtime['threshold'])['traces'][0]
        checks['http_cli_trace_identical'] = state['trace'] == expected == exported['trace']
        checks['bounded_termination'] = state['done'] and state['pulses'] <= len(runtime['parts'])
        requested = [s['next_channel'] for s in state['trace'] if s['next_channel'] is not None]
        checks['no_repeated_requests'] = len(requested) == len(set(requested))
        checks['unobserved_not_returned'] = all(r['value'] is None for r in start['state']['readings'] if not r['acquired'])
        manual = post('/api/start', {'mode': 'manual'})
        for label, reading in [('invalid_reading_rejected', 'not-a-number'), ('nonfinite_reading_rejected', 'NaN')]:
            try:
                post('/api/step', {'session': manual['session'], 'reading': reading})
                checks[label] = False
            except HTTPError as exc:
                checks[label] = exc.code == 400
        current = manual['state']
        part_index = {part['id']: i for i, part in enumerate(runtime['parts'])}
        while not current['done']:
            led_id = current['next_led']
            current = post('/api/step', {'session': manual['session'], 'led_id': led_id,
                                        'reading': runtime['example']['readings'][part_index[led_id]]})['state']
        checks['manual_replay_trace_identical'] = current['trace'] == expected
        changed = np.asarray(runtime['example']['readings']).copy()
        initial = runtime['bundle']['initial_indices']
        hidden = [j for j in range(len(changed)) if j not in initial]
        changed[hidden] += 100.
        altered = ScannerSession(runtime, ReplaySource(runtime['parts'], changed)).start()
        checks['unobserved_does_not_change_first_decision'] = altered['trace'][0] == expected[0]
        if not all(checks.values()):
            raise AssertionError('Scanner self-test failed: ' + str(checks))
        return {'status': 'passed', 'checks': checks, 'address': base,
                'model_manifest_sha256': runtime['manifest_sha256'], 'port_closed_after_test': True}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=10)


def serve(port=8765, self_test=False):
    runtime = load_runtime()
    if self_test:
        result = _http_test(runtime)
        atomic_json(ROOT / 'results/app_test.json', result)
        print('App self-test:', json.dumps(result['checks'], sort_keys=True))
        return result
    server = _make_server(runtime, port)
    print('Offline scanner app: http://127.0.0.1:%d' % server.server_port, flush=True)
    print('Press Ctrl-C to stop. Reads only the frozen model and development replay fixture.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    serve()
