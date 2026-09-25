"""모든 테마를 렌더해 4폭×2모드에서 넘침·대비·스크립트 오류와 주요 조작을 검사한다.
사용: .venv/bin/python tests/verify_render.py  (playwright 필요: uv run --with playwright)"""
import json, sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from doc_template.render import render
from doc_template.color import contrast

ROOT = Path(__file__).resolve().parents[1]
MD = (ROOT / 'examples' / 'sample-research.md').read_text()
THEMES = ['t1', 't2', 't3', 't4', 't5', 't6', 'paper', 'mono', 'one:t1', 'one:t3', 'one:#1957B8']
PAIRS = [('text', 'bg'), ('muted', 'bg'), ('accent', 'bg'), ('link', 'bg'), ('marktext', 'mark'), ('obitext', 'obi'), ('muted', 'panel')]
OV = '''() => { const w = innerWidth, bad = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('.table.compare') && !el.matches('.table.compare')) continue;
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    if (r.width && (r.right > w + 1 || r.left < -1) && cs.position !== 'fixed' && cs.visibility !== 'hidden') bad.push((el.className || el.tagName) + ':' + Math.round(r.right)); }
  return { page: document.documentElement.scrollWidth > w, bad: bad.slice(0, 5) }; }'''
tmp = Path(tempfile.mkdtemp()); fails = []; checks = 0; results = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    for th in THEMES:
        html, rep = render(MD, theme=th); f = tmp / (th.replace(':', '-').replace('#', '') + '.html'); f.write_text(html)
        for w in (1440, 768, 390, 360):
            for mode in ('light', 'dark'):
                pg = b.new_page(viewport={'width': w, 'height': 900}, color_scheme=mode); errs = []
                pg.on('pageerror', lambda e: errs.append(str(e))); pg.goto(f.as_uri(), wait_until='networkidle')
                ov = pg.evaluate(OV)
                v = pg.evaluate("""() => { const c = getComputedStyle(document.documentElement);
                  return Object.fromEntries(['bg','panel','text','muted','accent','mark','marktext','link','obi','obitext'].map(k => [k, c.getPropertyValue('--' + k).trim()])) }""")
                low = min(contrast(v[a], v[c]) for a, c in PAIRS); checks += len(PAIRS) + 2
                measure = pg.evaluate("(() => { const p = document.querySelector('.doc section p'); return p ? Math.round(p.getBoundingClientRect().width) : 0 })()")
                if ov['page'] or ov['bad'] or errs or low < 4.5:
                    fails.append(dict(theme=th, w=w, mode=mode, ov=ov, errs=errs[:2], low=round(low, 2)))
                results.append(dict(theme=th, w=w, mode=mode, low=round(low, 2), measure=measure))
                pg.close()
    # 흑백: 모든 요소의 지정 색이 검정·흰색·투명뿐인지
    fbw = tmp / 'mono.html'
    for mode in ('light', 'dark'):
        pg = b.new_page(viewport={'width': 1440, 'height': 900}, color_scheme=mode); pg.goto(fbw.as_uri(), wait_until='networkidle')
        bad = pg.evaluate('''() => { const ok = new Set(['rgb(0, 0, 0)','rgb(255, 255, 255)','rgba(0, 0, 0, 0)']); const out = new Set();
          for (const el of document.querySelectorAll('*')) { if (el.tagName === 'IMG') continue; const c = getComputedStyle(el);
            for (const p of ['color','backgroundColor','borderTopColor','borderLeftColor','borderBottomColor','textDecorationColor','outlineColor']) {
              const v = c[p]; if (!ok.has(v) && !(p.startsWith('border') && c[p.replace('Color','Width')] === '0px')) out.add(p + ' ' + v + ' ' + (el.className || el.tagName)); } }
          return [...out].slice(0, 6) }''')
        checks += 1
        if bad: fails.append({'bw': mode, 'colors': bad})
        pg.close()
    # 조작 (t1)
    f = tmp / 't1.html'; pg = b.new_page(viewport={'width': 1440, 'height': 900}); pg.goto(f.as_uri(), wait_until='networkidle')
    ok = lambda n, c: (fails.append({'interaction': n}) if not c else None)
    pg.click('#theme-btn'); ok('테마 전환', pg.evaluate('document.documentElement.dataset.theme') == 'dark')
    pg.click('#mark-btn'); ok('강조 끄기', pg.evaluate("getComputedStyle(document.querySelector('.doc mark')).backgroundColor") in ('rgba(0, 0, 0, 0)', 'transparent'))
    pg.click('.toc a[href="#s3"]'); pg.wait_for_timeout(1500); ok('목차 현재 위치', pg.get_attribute('.toc a[href="#s3"]', 'aria-current') == 'true')
    pg.evaluate('scrollTo(0, innerHeight * 3)'); pg.wait_for_timeout(300); ok('맨 위로 버튼 표시', pg.evaluate("document.getElementById('to-top').classList.contains('show')"))
    pg.set_viewport_size({'width': 390, 'height': 844}); pg.goto(f.as_uri())
    pg.click('.toc-mobile summary'); ok('모바일 목차 열기', pg.evaluate("document.querySelector('.toc-mobile').open"))
    ok('비교표 첫 열 고정', pg.evaluate("getComputedStyle(document.querySelector('.table.compare td')).position") == 'sticky')
    pg.emulate_media(media='print'); ok('인쇄 흰 바탕', pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()").upper() == '#FFFFFF')
    b.close()
print(json.dumps({'renders': len(THEMES), 'runs': len(results), 'checks': checks, 'fails': fails[:8],
                  'min_contrast': min(r['low'] for r in results),
                  'measure_px_desktop': sorted({r['measure'] for r in results if r['w'] == 1440})}, ensure_ascii=False, indent=1))
sys.exit(1 if fails else 0)
