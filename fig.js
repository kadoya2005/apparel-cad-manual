// アパレルCAD マニュアル：キャプチャに番号の枠を重ねる・目次の現在地・画像の拡大
//   <figure data-shot="role" data-crop="x,y,w,h" data-marks="tool:1,line:2"> … </figure>
//   shot  … shots.js（capture.py が書き出す）の名前。画像は img/<shot>.png
//   crop  … 見せる範囲（キャプチャ上の CSS px）。なければ全体
//   marks … 「枠の名前:番号」をカンマ区切り。枠の名前は shots.js の r、または x;y;w;h の数字
(function () {
  function rectOf(shot, key) {
    if (/^[\d.;-]+$/.test(key)) return key.split(';').map(Number);
    return shot.r[key];
  }
  function build(fig) {
    const shot = window.SHOTS && window.SHOTS[fig.dataset.shot];
    if (!shot) return;
    const crop = fig.dataset.crop ? fig.dataset.crop.split(',').map(Number) : [0, 0, shot.w, shot.h];
    const [cx, cy, cw, ch] = crop;
    const box = document.createElement('div');
    box.className = 'shot zoomable';
    box.style.aspectRatio = cw + ' / ' + ch;
    const clipEl = document.createElement('div');
    clipEl.className = 'clip';
    box.appendChild(clipEl);
    const img = document.createElement('img');
    img.src = 'img/' + fig.dataset.shot + '.png';
    img.alt = fig.dataset.alt || fig.querySelector('figcaption')?.textContent.trim().split('\n')[0] || '';
    img.loading = 'eager';   // 印刷（PDF）でも全部の画像が出るように
    img.style.width = (shot.w / cw * 100) + '%';
    img.style.left = (-cx / cw * 100) + '%';
    img.style.top = (-cy / ch * 100) + '%';
    clipEl.appendChild(img);
    (fig.dataset.marks || '').split(',').filter(Boolean).forEach((m) => {
      const i = m.lastIndexOf(':');
      let r = rectOf(shot, m.slice(0, i));
      if (!r) return;
      // 見せる範囲からはみ出す枠は、範囲の中に収める（はみ出しすぎるものは描かない）
      const x0 = Math.max(r[0], cx), y0 = Math.max(r[1], cy), x1 = Math.min(r[0] + r[2], cx + cw), y1 = Math.min(r[1] + r[3], cy + ch);
      if (x1 - x0 < 4 || y1 - y0 < 4) return;
      r = [x0, y0, x1 - x0, y1 - y0];
      const pad = 4;
      const el = document.createElement('div');
      el.className = 'mk';
      el.style.left = ((r[0] - pad - cx) / cw * 100) + '%';
      el.style.top = ((r[1] - pad - cy) / ch * 100) + '%';
      el.style.width = ((r[2] + 2 * pad) / cw * 100) + '%';
      el.style.height = ((r[3] + 2 * pad) / ch * 100) + '%';
      el.innerHTML = '<i>' + m.slice(i + 1) + '</i>';
      box.appendChild(el);
    });
    box.addEventListener('click', () => openLight(img.src));
    fig.insertBefore(box, fig.firstChild);
  }
  function openLight(src) {
    const lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.innerHTML = '<img alt="">';
    lb.firstChild.src = src;
    lb.addEventListener('click', () => lb.remove());
    document.addEventListener('keydown', function esc(e) { if (e.key === 'Escape') { lb.remove(); document.removeEventListener('keydown', esc); } });
    document.body.appendChild(lb);
  }
  document.querySelectorAll('figure[data-shot]').forEach(build);
  document.querySelectorAll('img.zoomable').forEach((im) => im.addEventListener('click', () => openLight(im.src)));

  // 目次：いま読んでいる章に色を付ける
  const links = [...document.querySelectorAll('.toc a[href^="#"]')];
  const targets = links.map((a) => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if (targets.length && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((ents) => {
      ents.forEach((e) => {
        if (!e.isIntersecting) return;
        links.forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id));
      });
    }, { rootMargin: '-70px 0px -70% 0px' });
    targets.forEach((t) => io.observe(t));
  }
})();
