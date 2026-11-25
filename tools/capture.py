# アパレルCAD マニュアル用の画面キャプチャを撮る
#
# 使い方（apparel-cad フォルダーで）：
#   1. python -m http.server 8745 --bind 127.0.0.1    （別のウィンドウで動かしておく）
#   2. python manual/tools/capture.py
# Edge を画面なしで起動し、本物のマウス操作を送って、manual/img/ に PNG を、manual/shots.js に枠の位置を書きます。
import json, os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import launch, close

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # manual/
IMG = os.path.join(ROOT, 'img')
URL = 'http://127.0.0.1:8745/index.html'
W, H, DPR = 1440, 900, 2
os.makedirs(IMG, exist_ok=True)

# ページの中で使う道具（型紙の mm 座標 → 画面の px、要素の枠）
HELPERS = r"""
window.__K = PT_PER_MM;
window.__M = (x, y, ox = 30) => { const r = stage.getBoundingClientRect(); const s = toScr(P((ox + x) * __K, (50 + y) * __K)); return [r.left + s.x, r.top + s.y]; };
window.__R = (el) => { if (typeof el === 'string') el = document.querySelector(el); if (!el) return null; const b = el.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; };
window.__U = (list) => { const bs = list.map(__R).filter(Boolean); const x0 = Math.min(...bs.map(b => b[0])), y0 = Math.min(...bs.map(b => b[1])), x1 = Math.max(...bs.map(b => b[0] + b[2])), y1 = Math.max(...bs.map(b => b[1] + b[3])); return [x0, y0, x1 - x0, y1 - y0]; };
window.__fitTo = (g, pad = 70) => { const bb = Geo.bbox(leaves([g])); const r = stage.getBoundingClientRect(); const z = Math.min((r.width - 2 * pad) / bb.w, (r.height - 2 * pad) / bb.h); view.z = z; view.x = r.width / 2 - (bb.x + bb.w / 2) * z; view.y = r.height / 2 - (bb.y + bb.h / 2) * z; renderView(); };
window.__ptRect = (pts, pad = 10) => { const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]); return [Math.round(Math.min(...xs) - pad), Math.round(Math.min(...ys) - pad), Math.round(Math.max(...xs) - Math.min(...xs) + 2 * pad), Math.round(Math.max(...ys) - Math.min(...ys) + 2 * pad)]; };
1
"""

def save_shots(shots):
    """shots.js に書く。ほかのスクリプト（capture_tutorial.py）が撮った分は残して、同じ名前だけ入れ替える"""
    path = os.path.join(ROOT, 'shots.js')
    allv = {}
    if os.path.exists(path):
        t = open(path, encoding='utf-8').read()
        allv = json.loads(t[t.index('=') + 1:t.rindex(';')])
    allv.update(shots)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('// manual/tools/capture.py・capture_tutorial.py が書き出す、キャプチャの大きさと枠の位置（CSS px）\n')
        f.write('window.SHOTS = ' + json.dumps(allv, ensure_ascii=False, indent=1) + ';\n')

def main():
    proc, c = launch(W, H, dpr=DPR)
    c.call('Network.enable'); c.call('Network.setCacheDisabled', {'cacheDisabled': True})
    shots = {}
    try:
        def go():
            c.call('Page.navigate', {'url': URL})
            time.sleep(1.5)
            c.js("try { localStorage.clear(); } catch (e) {} 1")
            c.call('Page.reload', {'ignoreCache': True})
            time.sleep(1.5)
            c.js(HELPERS)
            c.js("window.confirm = () => true; 1")
        def mouse(kind, x, y, buttons=1):
            c.call('Input.dispatchMouseEvent', {'type': kind, 'x': x, 'y': y, 'button': 'left' if kind != 'mouseMoved' else 'none', 'buttons': buttons if kind != 'mouseReleased' else 0, 'clickCount': 1})
        def click(x, y):
            mouse('mouseMoved', x, y, 0); mouse('mousePressed', x, y); mouse('mouseReleased', x, y); time.sleep(0.15)
        def drag(x0, y0, x1, y1, steps=12):
            mouse('mouseMoved', x0, y0, 0); mouse('mousePressed', x0, y0)
            for i in range(1, steps + 1):
                mouse('mouseMoved', x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps, 1)
            mouse('mouseReleased', x1, y1); time.sleep(0.15)
        def click_el(sel):
            x, y, w, h = c.js(f"__R({json.dumps(sel)})")
            click(x + w / 2, y + h / 2)
        def M(x, y, ox=30):
            return c.js(f"__M({x}, {y}, {ox})")
        def R(sel):
            return c.js(f"__R({json.dumps(sel)})")
        def shot(name, rects, clip=None):
            path = os.path.join(IMG, name + '.png')
            c.shot(path, clip=clip, scale=1)
            with open(path, 'rb') as f:
                pw, ph_ = struct.unpack('>II', f.read(24)[16:24])   # PNG の大きさ（DPR 倍）→ CSS px に戻す
            shots[name] = {'w': round(pw / DPR), 'h': round(ph_ / DPR), 'r': rects}
            print('shot', name)

        # ---- 1. 画面全体（画面対応マニュアル用）：パネルが全部見えるように縦を長く ----
        go()
        click_el('#btnPatSample'); time.sleep(0.4)
        ph = c.js("document.getElementById('panels').scrollHeight + document.getElementById('topbar').offsetHeight + document.getElementById('status').offsetHeight")
        tall = max(H, int(ph) + 4)
        c.call('Emulation.setDeviceMetricsOverride', {'width': W, 'height': tall, 'deviceScaleFactor': DPR, 'mobile': False})
        time.sleep(0.4); c.js("fitView(); 1"); time.sleep(0.3)
        rects = c.js(r"""(() => {
          const o = {};
          o.brand = __R('.brand'); o.file = __U(['[data-cmd=new]', '[data-cmd=saveAs]']); o.exportSvg = __R('[data-cmd=exportSvg]'); o.exportAama = __R('[data-cmd=exportAama]');
          o.menus = __U(['[data-menu=object]', '[data-menu=view]']); o.undo = __U(['#btnUndo', '#btnRedo']); o.outline = __R('#btnOutline'); o.zoom = __R('#zoomLabel');
          o.fileName = __R('#fileName'); o.prefs = __R('[data-cmd=prefs]'); o.help = __R('[data-cmd=help]');
          document.querySelectorAll('[data-tool]').forEach(b => { o['tool_' + b.dataset.tool] = __R(b); });
          o.colors = __R('#colorWell') || __U(['#swFill', '#btnNone']);
          o.canvas = __R('#board'); o.status = __R('#status');
          o.patSample = __R('#btnPatSample'); o.patRole = __R('#patRole'); o.patName = __R('#patName'); o.patQty = __R('#patQty');
          o.patNotch = __R('#patNotchMode'); o.patEnc = __R('#patEncoding'); o.spread = __R('#btnSpread'); o.seam = __R('#btnSeam'); o.aama = __R('#btnAama');
          const secs = [...document.querySelectorAll('#panels section')];
          ['pattern', 'fillstroke', 'transform', 'align', 'pathfinder', 'artboard', 'layers'].forEach((k, i) => { o['sec_' + k] = __R(secs[i]); });
          return o; })()""")
        shot('app', rects, None)
        c.call('Emulation.setDeviceMetricsOverride', {'width': W, 'height': H, 'deviceScaleFactor': DPR, 'mobile': False})
        time.sleep(0.3)

        # ---- 2. ペンで描く（新規の紙に、描いている途中）----
        go()
        c.js("doc.width = 300 * __K; doc.height = 220 * __K; fitView(); render(); 1"); time.sleep(0.2)
        pen = R('[data-tool=pen]')
        click(pen[0] + pen[2] / 2, pen[1] + pen[3] / 2)
        P0 = M(20, 160, 0); P1 = M(20, 40, 0); P2 = M(140, 20, 0); P2h = M(200, 20, 0); P3 = M(250, 60, 0); P4 = M(250, 160, 0)
        click(*P0); click(*P1); drag(P2[0], P2[1], P2h[0], P2h[1]); click(*P3); click(*P4)
        mouse('mouseMoved', P0[0] + 30, P0[1] - 6, 0); time.sleep(0.1)
        mouse('mouseMoved', P0[0] + 2, P0[1] + 1, 0); time.sleep(0.2)
        shot('pen', {'tool': pen, 'start': c.js(f"__ptRect([[{P0[0]},{P0[1]}]], 16)"), 'curve': c.js(f"__ptRect([[{P2[0]},{P2[1]}],[{P2h[0]},{P2h[1]}]], 14)")})
        click(P0[0], P0[1]); time.sleep(0.2)
        shot('pen_closed', {'tool': pen})

        # ---- 3. 線の役割：ダイレクト選択で縫い線を選ぶ ----
        go()
        click_el('#btnPatSample'); time.sleep(0.3)
        c.js("__fitTo(doc.layers[0].items[0], 60); 1"); time.sleep(0.2)
        click_el('[data-tool=direct]')
        sp = M(120, 600)   # 縫い線の裾
        click(*sp); time.sleep(0.3)
        role = c.js("(selectedItems()[0] || {}).pat ? selectedItems()[0].pat.role : ''")
        print('selected role', role)
        shot('role', {'tool': R('[data-tool=direct]'), 'line': c.js(f"__ptRect([[{sp[0]},{sp[1]}]], 18)"), 'patRole': R('#patRole'), 'patName': R('#patName'), 'patQty': R('#patQty')})

        # ---- 4. 切り開き線を引く（直線ツールで裾 → ウエスト）----
        click_el('[data-tool=line]')
        a0, a1 = M(80, 600), M(80, 9)
        b0, b1 = M(160, 600), M(160, 5)
        drag(a0[0], a0[1], a1[0], a1[1], 20)
        c.js("$('patRole').value = 'slash'; $('patRole').dispatchEvent(new Event('change')); 1")
        drag(b0[0], b0[1], b1[0], b1[1], 20)
        c.js("$('patRole').value = 'slash'; $('patRole').dispatchEvent(new Event('change')); 1"); time.sleep(0.2)
        n = c.js("allItems().filter(i => i.pat && i.pat.role === 'slash').length"); print('slash lines', n)
        shot('slash', {'tool': R('[data-tool=line]'), 'lines': c.js(f"__ptRect([[{a0[0]},{a0[1]}],[{b1[0]},{b1[1]}]], 14)"), 'hem': c.js(f"__ptRect([[{a0[0]},{a0[1]}],[{b0[0]},{b0[1]}]], 16)"), 'patRole': R('#patRole')})

        # ---- 5. 型紙を選んで「切り開き…」→ プレビュー ----
        click_el('[data-tool=select]')
        sd = M(255, 400); click(*sd); time.sleep(0.2)
        click_el('#btnSpread'); time.sleep(0.4)
        click_el('#dlgPreview'); time.sleep(0.5)
        shot('dialog', {'spread': R('#btnSpread'), 'open': R('#dlg_open'), 'seam': R('#dlg_seam'), 'preview': R('#dlgPreview'), 'ok': R('#dlgOK'), 'box': R('#dialog .modalBox')})
        click_el('#dlgOK'); time.sleep(0.4)
        c.js("deselectAll(); __fitTo(doc.layers[0].items[0], 60); 1"); time.sleep(0.3)
        shot('flare', {'hem': c.js("__ptRect([__M(0, 600), __M(330, 565)], 24)"), 'waist': c.js("__ptRect([__M(80, 9), __M(225, -22)], 22)")})

        # ---- 6. 書き出し（型紙パネル）----
        clip = c.js("(() => { const r = __R('#panels section'); return [r[0], r[1], r[2], r[3]]; })()")
        rel = lambda r: [r[0] - clip[0], r[1] - clip[1], r[2], r[3]]
        shot('panel', {k: rel(R(s)) for k, s in [('sample', '#btnPatSample'), ('role', '#patRole'), ('name', '#patName'), ('qty', '#patQty'), ('notch', '#patNotchMode'), ('enc', '#patEncoding'), ('spread', '#btnSpread'), ('seam', '#btnSeam'), ('aama', '#btnAama')]}, clip=clip)
    finally:
        close(proc)
    save_shots(shots)
    print('done', list(shots))

if __name__ == '__main__':
    main()
