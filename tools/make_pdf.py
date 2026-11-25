# マニュアルの HTML を、Edge で印刷して PDF にする
#
# 使い方（apparel-cad フォルダーで）：
#   1. python -m http.server 8745 --bind 127.0.0.1    （別のウィンドウで動かしておく）
#   2. python manual/tools/make_pdf.py
# manual/ に concept.pdf・quickstart.pdf・tutorial.pdf・guide.pdf ができます。
import base64, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import launch, close

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # manual/
BASE = 'http://127.0.0.1:8745/manual/'
PAGES = [('concept.html', 'concept.pdf'), ('quickstart.html', 'quickstart.pdf'), ('tutorial.html', 'tutorial.pdf'), ('guide.html', 'guide.pdf')]

def main():
    proc, c = launch(1280, 900, port=9334)
    try:
        # 前に読んだ HTML や画像を使い回さない（直したのに PDF が古いままになるのを防ぐ）
        c.call('Network.enable'); c.call('Network.setCacheDisabled', {'cacheDisabled': True})
        for html, pdf in PAGES:
            c.call('Page.navigate', {'url': BASE + html})
            # 画像が全部読み込まれるまで待つ
            for _ in range(60):
                time.sleep(0.25)
                done = c.js("document.readyState === 'complete' && [...document.images].every(i => i.complete && i.naturalWidth > 0)")
                if done: break
            time.sleep(0.5)
            r = c.call('Page.printToPDF', {'printBackground': True, 'preferCSSPageSize': True, 'displayHeaderFooter': False})
            out = os.path.join(ROOT, pdf)
            with open(out, 'wb') as f:
                f.write(base64.b64decode(r['data']))
            print(pdf, os.path.getsize(out) // 1024, 'KB')
    finally:
        close(proc)

if __name__ == '__main__':
    main()
