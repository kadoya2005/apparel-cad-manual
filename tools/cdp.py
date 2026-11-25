# 画面キャプチャ用の、小さな Chrome DevTools Protocol クライアント（Python の標準機能だけ）
import base64, json, os, socket, struct, subprocess, sys, time, urllib.request

class CDP:
    def __init__(self, ws_url):
        host_port, path = ws_url[len('ws://'):].split('/', 1)
        host, port = host_port.split(':')
        self.s = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f'GET /{path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
               f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
        self.s.sendall(req.encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.s.recv(4096)
        self.rest = buf.split(b'\r\n\r\n', 1)[1]
        self.id = 0

    def _recv_exact(self, n):
        while len(self.rest) < n:
            chunk = self.s.recv(1 << 20)
            if not chunk:
                raise ConnectionError('closed')
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def _recv_msg(self):
        data = b''
        while True:
            b1, b2 = self._recv_exact(2)
            fin, op, ln = b1 & 0x80, b1 & 0x0f, b2 & 0x7f
            if ln == 126: ln = struct.unpack('>H', self._recv_exact(2))[0]
            elif ln == 127: ln = struct.unpack('>Q', self._recv_exact(8))[0]
            payload = self._recv_exact(ln)
            if op == 9:  # ping
                continue
            data += payload
            if fin:
                return data.decode('utf-8')

    def call(self, method, params=None):
        self.id += 1
        msg = json.dumps({'id': self.id, 'method': method, 'params': params or {}}).encode()
        hdr = bytearray([0x81])
        n = len(msg)
        if n < 126: hdr.append(0x80 | n)
        elif n < 65536: hdr += bytes([0x80 | 126]) + struct.pack('>H', n)
        else: hdr += bytes([0x80 | 127]) + struct.pack('>Q', n)
        mask = os.urandom(4)
        hdr += mask
        self.s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(msg)))
        while True:
            r = json.loads(self._recv_msg())
            if r.get('id') == self.id:
                if 'error' in r:
                    raise RuntimeError(f'{method}: {r["error"]}')
                return r.get('result', {})

    def js(self, expr):
        r = self.call('Runtime.evaluate', {'expression': expr, 'awaitPromise': True, 'returnByValue': True})
        if 'exceptionDetails' in r:
            raise RuntimeError(json.dumps(r['exceptionDetails'], ensure_ascii=False)[:800])
        return r.get('result', {}).get('value')

    def shot(self, path, clip=None, scale=1):
        p = {'format': 'png'}
        if clip:
            p['clip'] = {'x': clip[0], 'y': clip[1], 'width': clip[2], 'height': clip[3], 'scale': scale}
        r = self.call('Page.captureScreenshot', p)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(r['data']))


def launch(width=1440, height=900, port=9333, dpr=1):
    exe = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    prof = os.path.join(os.environ.get('TEMP', '.'), 'apparelcad-capture-profile')
    proc = subprocess.Popen([exe, '--headless=new', f'--remote-debugging-port={port}', f'--user-data-dir={prof}',
                             f'--window-size={width},{height}', f'--force-device-scale-factor={dpr}',
                             '--no-first-run', '--hide-scrollbars', 'about:blank'])
    for _ in range(50):
        try:
            tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
            page = next(t for t in tabs if t.get('type') == 'page')
            c = CDP(page['webSocketDebuggerUrl'])
            c.call('Page.enable'); c.call('Runtime.enable')
            c.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height, 'deviceScaleFactor': dpr, 'mobile': False})
            return proc, c
        except Exception:
            time.sleep(0.3)
    raise RuntimeError('Edge did not start')
