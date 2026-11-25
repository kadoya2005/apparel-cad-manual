# AAMA DXF の中身を、画層ごとに色分けした SVG にする（マニュアルの図用）
#   python manual/tools/dxf_preview.py 入力.dxf 出力.svg
import sys

COLORS = {'1': ('#1d2129', 1.6), '14': ('#8a94a6', 1.0), '8': ('#2f6fff', 1.2), '7': ('#d93a2b', 1.6), '4': ('#0f9d58', 0), '2': ('#f08c00', 0), '3': ('#c4c9d1', 0)}

def read_pairs(path):
    raw = open(path, 'rb').read()
    try: text = raw.decode('cp932')
    except UnicodeDecodeError: text = raw.decode('utf-8')
    t = text.split('\r\n')
    return [(int(t[i]), t[i + 1]) for i in range(0, len(t) - 1, 2)]

def entities(ps):
    out, i = [], 0
    while i < len(ps):
        c, v = ps[i]
        if c == 0 and v in ('POLYLINE', 'POINT', 'LINE'):
            d, j = {}, i + 1
            while ps[j][0] != 0: d.setdefault(ps[j][0], ps[j][1]); j += 1
            e = {'t': v, 'layer': d.get(8), 'd': d}
            if v == 'POLYLINE':
                pts = []
                while ps[j][1] == 'VERTEX':
                    dd = {}; j += 1
                    while ps[j][0] != 0: dd[ps[j][0]] = ps[j][1]; j += 1
                    pts.append((float(dd[10]), float(dd[20])))
                e['pts'] = pts
            out.append(e); i = j; continue
        i += 1
    return out

def main(src, dst):
    es = entities(read_pairs(src))
    xs = [p[0] for e in es if e['t'] == 'POLYLINE' for p in e['pts']]
    ys = [p[1] for e in es if e['t'] == 'POLYLINE' for p in e['pts']]
    m = 12
    x0, x1, y0, y1 = min(xs) - m, max(xs) + m, min(ys) - m, max(ys) + m
    Y = lambda y: round(y1 - y + y0, 2)   # DXF は y が上向きなので反転
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {x1 - x0:.1f} {y1 - y0:.1f}" style="background:#fff">']
    for e in es:
        col, w = COLORS.get(e['layer'], ('#ff00ff', 1))
        d = e['d']
        if e['t'] == 'POLYLINE':
            pts = ' '.join(f'{x:.2f},{Y(y)}' for x, y in e['pts'])
            o.append(f'<polyline fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" points="{pts}"/>')
        elif e['t'] == 'LINE':
            o.append(f'<line stroke="{col}" stroke-width="{w}" x1="{d[10]}" y1="{Y(float(d[20]))}" x2="{d[11]}" y2="{Y(float(d[21]))}"/>')
        elif e['t'] == 'POINT':
            r = {'4': 4.5, '2': 3}.get(e['layer'], 0)
            if r: o.append(f'<circle fill="{col}" r="{r}" cx="{d[10]}" cy="{Y(float(d[20]))}"/>')
    o.append('</svg>')
    open(dst, 'w', encoding='utf-8').write('\n'.join(o))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
