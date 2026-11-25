# 「見本ができるまで」（tutorial.html）の画面を撮る
#   白紙から前スカートを 1 枚作り、切り開いて書き出すまでを、本物のマウスとキーボードの操作で進めて 1 手順ずつ撮る
# 使い方：capture.py と同じ（サーバーを動かしてから python manual/tools/capture_tutorial.py）
import json, os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import launch, close
from capture import HELPERS, IMG, URL, W, H, DPR, save_shots

def main():
    proc, c = launch(W, H, port=9336, dpr=DPR)
    c.call('Network.enable'); c.call('Network.setCacheDisabled', {'cacheDisabled': True})
    shots = {}

    def mouse(kind, x, y, buttons=1):
        c.call('Input.dispatchMouseEvent', {'type': kind, 'x': x, 'y': y, 'button': 'left' if kind != 'mouseMoved' else 'none', 'buttons': buttons if kind != 'mouseReleased' else 0, 'clickCount': 1})
    def click(x, y):
        mouse('mouseMoved', x, y, 0); mouse('mousePressed', x, y); mouse('mouseReleased', x, y); time.sleep(0.15)
    def drag(x0, y0, x1, y1, steps=16):
        mouse('mouseMoved', x0, y0, 0); mouse('mousePressed', x0, y0)
        for i in range(1, steps + 1):
            mouse('mouseMoved', x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps, 1)
        mouse('mouseReleased', x1, y1); time.sleep(0.15)
    def key(k, code, vk, mods=0):
        # mods：Alt=1 Ctrl=2 Shift=8。修飾キーも押して離す（離さないとアプリが「押したまま」と思い込む）
        held = [m for m in [(2, 'Control', 'ControlLeft', 17), (8, 'Shift', 'ShiftLeft', 16)] if mods & m[0]]
        acc = 0
        for bit, kk, cc, vv in held:
            acc |= bit
            c.call('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': kk, 'code': cc, 'windowsVirtualKeyCode': vv, 'modifiers': acc})
        c.call('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': k, 'code': code, 'windowsVirtualKeyCode': vk, 'modifiers': mods})
        c.call('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': k, 'code': code, 'windowsVirtualKeyCode': vk, 'modifiers': mods})
        for bit, kk, cc, vv in reversed(held):
            acc &= ~bit
            c.call('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': kk, 'code': cc, 'windowsVirtualKeyCode': vv, 'modifiers': acc})
        time.sleep(0.15)
    def R(sel):
        return c.js(f"__R({json.dumps(sel)})")
    def click_el(sel):
        c.js(f"document.querySelector({json.dumps(sel)}).scrollIntoView({{block: 'nearest'}}); 1")   # パネルの下のほうにあるときは見える所まで
        x, y, w, h = R(sel)
        click(x + w / 2, y + h / 2)
    def type_into(sel, text):
        click_el(sel)
        key('a', 'KeyA', 65, 2)                      # 入力欄の中を全部選ぶ
        c.call('Input.insertText', {'text': text})
        key('Enter', 'Enter', 13)
    def M(x, y):
        return c.js(f"__M({x}, {y})")
    def pts(*ps, pad=14):
        return c.js(f"__ptRect({json.dumps([list(p) for p in ps])}, {pad})")
    def role(r):
        c.js(f"$('patRole').value = '{r}'; $('patRole').dispatchEvent(new Event('change')); 1"); time.sleep(0.15)
    def shot(name, rects, keep_toast=False):
        if not keep_toast:
            c.js("document.getElementById('toast').classList.remove('show'); 1")   # 前の操作の知らせを消す
        time.sleep(0.25)
        path = os.path.join(IMG, name + '.png')
        c.shot(path)
        with open(path, 'rb') as f:
            pw, ph = struct.unpack('>II', f.read(24)[16:24])
        shots[name] = {'w': round(pw / DPR), 'h': round(ph / DPR), 'r': rects}
        print('shot', name)
    def fit_piece():
        c.js("(() => { const its = allItems(); if (!its.length) return fitView(); const bb = Geo.bbox(its); const r = stage.getBoundingClientRect(); const z = Math.min((r.width - 160) / bb.w, (r.height - 140) / bb.h); view.z = z; view.x = r.width / 2 - (bb.x + bb.w / 2) * z; view.y = r.height / 2 - (bb.y + bb.h / 2) * z; renderView(); })(); 1")
        time.sleep(0.2)

    try:
        c.call('Page.navigate', {'url': URL})
        time.sleep(1.5)
        c.js("try { localStorage.clear(); } catch (e) {} 1")
        c.call('Page.reload', {'ignoreCache': True}); time.sleep(1.5)
        c.js(HELPERS); c.js("window.confirm = () => true; 1")

        # 1. 新規 → アートボードを 400×700mm（1133.86×1984.25pt）に
        click_el('[data-cmd=new]'); time.sleep(0.3)
        type_into('#inBW', '1133.86'); type_into('#inBH', '1984.25')
        key('0', 'Digit0', 48, 2); time.sleep(0.3)               # Ctrl+0：全体を表示
        shot('t01', {'new': R('[data-cmd=new]'), 'board': c.js("__R(document.querySelectorAll('#panels section')[5])")})
        c.js("document.getElementById('panels').scrollTop = 0; 1")   # パネルを上に戻す（型紙パネルが見えるように）

        # 2. ペンで縫い線を描く（中心ウエスト → 脇ウエスト → 腰（ドラッグで曲線）→ 脇の裾 → 中心の裾 → 始点で閉じる）
        click_el('[data-tool=pen]')
        A, B, C, Ch, D, E = M(0, 10), M(230, 0), M(245, 190), M(245, 250), M(245, 600), M(0, 600)
        click(*A); click(*B); drag(C[0], C[1], Ch[0], Ch[1]); click(*D)
        mouse('mouseMoved', E[0] + 40, E[1] - 20, 0); time.sleep(0.15)
        shot('t02', {'tool': R('[data-tool=pen]'), 'curve': pts(C, Ch, pad=16)})
        click(*E); mouse('mouseMoved', A[0] + 3, A[1] + 2, 0); time.sleep(0.2)
        click(*A); time.sleep(0.2)
        key('a', 'KeyA', 65, 2 | 8)                                # Ctrl+Shift+A：選択をやめる
        # 3. ダーツ（ペンで 3 点、Esc で終わり）
        d0, d1, d2 = M(93, 6), M(103, 110), M(113, 5.1)
        click(*d0); click(*d1); click(*d2); key('Escape', 'Escape', 27)
        key('a', 'KeyA', 65, 2 | 8)
        # 4. 布目線（直線で下から上へ）
        click_el('[data-tool=line]')
        g0, g1 = M(60, 520), M(60, 150)
        drag(g0[0], g0[1], g1[0], g1[1], 20)
        # 塗りをなしに（全部選んで「なし」）
        click_el('[data-tool=select]'); key('a', 'KeyA', 65, 2); click_el('#fillNone'); key('a', 'KeyA', 65, 2 | 8)
        fit_piece()
        shot('t03', {'dart': pts(d0, d1, d2), 'grain': pts(g0, g1, pad=10)})

        # 5. 役割を付ける（まだグループにしていないので、選択ツールで 1 本ずつ選べる）
        sw = M(120, 600); dt = M(103, 110); gr = M(60, 330)
        click(*sw); role('sew'); click(*dt); role('internal'); click(*gr); role('grain')
        shot('t04', {'line': pts(gr, pad=14), 'patRole': R('#patRole')})

        # 6. 縫い代：縫い線を選んで「縫い代…」→ 10mm → OK
        click(*sw); time.sleep(0.1)
        click_el('#btnSeam'); time.sleep(0.3); c.js("document.getElementById('panels').scrollTop = 0; 1")
        shot('t05', {'seam': R('#btnSeam'), 'field': R('#dlg_seam'), 'ok': R('#dlgOK'), 'line': pts(sw, pad=14)})
        click_el('#dlgOK'); time.sleep(0.3)
        key('a', 'KeyA', 65, 2 | 8)
        cut_side = M(255, 400)
        shot('t06', {'cut': pts(M(255, 300), M(255, 500), pad=12), 'sew': pts(M(245, 300), M(245, 500), pad=8)})

        # 7. ノッチ（直線で、輪郭の上から内側へ 5mm）
        click_el('[data-tool=line]')
        n1a, n1b, n2a, n2b = M(255, 190), M(250, 190), M(-10, 190), M(-5, 190)
        drag(n1a[0], n1a[1], n1b[0], n1b[1], 6); role('notch')
        drag(n2a[0], n2a[1], n2b[0], n2b[1], 6); role('notch')
        shot('t07', {'n1': pts(n1a, n1b, pad=16), 'n2': pts(n2a, n2b, pad=16), 'patRole': R('#patRole')})

        # 8. 1 枚にまとめる（全部選んで Ctrl+G）→ 名前と枚数
        click_el('[data-tool=select]'); key('a', 'KeyA', 65, 2); key('g', 'KeyG', 71, 2)
        type_into('#patName', '前スカート'); type_into('#patQty', '1')
        groups = c.js("doc.layers[0].items.map(n => n.type || 'path')"); print('top', groups)
        shot('t08', {'name': R('#patName'), 'qty': R('#patQty'), 'piece': pts(M(-10, -12), M(255, 610), pad=6)})

        # 9. 切り開き線（直線で裾 → ウエスト）
        key('a', 'KeyA', 65, 2 | 8)
        click_el('[data-tool=line]')
        s1a, s1b, s2a, s2b = M(80, 600), M(80, 6.5), M(160, 600), M(160, 3)
        drag(s1a[0], s1a[1], s1b[0], s1b[1], 20); role('slash')
        drag(s2a[0], s2a[1], s2b[0], s2b[1], 20); role('slash')
        shot('t09', {'lines': pts(s1a, s2b, pad=14), 'patRole': R('#patRole')})

        # 10. 切り開き（型紙を選んで「切り開き…」→ 60mm・10mm → OK）
        click_el('[data-tool=select]'); click(*cut_side); time.sleep(0.1)
        click_el('#btnSpread'); time.sleep(0.3)
        click_el('#dlgPreview'); time.sleep(0.4)
        shot('t10', {'spread': R('#btnSpread'), 'open': R('#dlg_open'), 'ok': R('#dlgOK')})
        click_el('#dlgOK'); time.sleep(0.3)
        key('a', 'KeyA', 65, 2 | 8); fit_piece()
        shot('t11', {'hem': pts(M(0, 600), M(330, 560), pad=22)}, keep_toast=True)

        # 12. 書き出し
        shot('t12', {'aama': R('#btnAama'), 'notch': R('#patNotchMode'), 'enc': R('#patEncoding')})
        n = c.js("buildAamaDxf(doc, {}).pieces.map(p => p.name + ':' + p.roles.join('/'))"); print('dxf', n)
    finally:
        close(proc)
    save_shots(shots)

if __name__ == '__main__':
    main()
