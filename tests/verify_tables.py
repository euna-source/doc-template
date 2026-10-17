"""표 깨짐 검사(실제 브라우저): 화면 폭마다 ① 페이지 가로 넘침 ② 표 잘림(감싸개 안 가로 스크롤) ③ 칸 선 끊김(병합 칸 포함) ④ 칸 밖으로 넘친 내용.
쓰기: uv run --with playwright python tests/verify_tables.py 파일.html … [--widths 320,390,600,768,1024,1440] [--browsers chrome,webkit] [--shots 폴더]
끝 줄 TABLES_OK 또는 TABLES_FAIL n."""
import argparse, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

AUDIT = r"""() => {
  const W = document.documentElement.clientWidth, res = {page: document.documentElement.scrollWidth - W, tables: []};
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  [...document.querySelectorAll('table')].forEach((t, ti) => {
    if (!vis(t)) return;
    if (t.parentElement && t.parentElement.closest('td,th')) return;
    if (t.closest('[data-dk-skip], .sthwrap')) { res.skipped = (res.skipped || 0) + 1; return; }   // 원본 설계(옆으로 넘겨 보는 큰 표)
    const out = {i: ti, cls: (t.parentElement.className || '') + '', clip: 0, gaps: [], spill: [], stack: getComputedStyle(t).display === 'block'};
    let a = t.parentElement;
    while (a && a !== document.body) { const cs = getComputedStyle(a); if (/(auto|scroll|hidden)/.test(cs.overflowX) && a.scrollWidth > a.clientWidth + 2) { out.clip = a.scrollWidth - a.clientWidth; out.clipCls = a.className + ''; break; } a = a.parentElement; }
    const cells = [...t.querySelectorAll('th,td')].filter(c => c.closest('table') === t && vis(c)).map(c => ({c, b: c.getBoundingClientRect(), s: getComputedStyle(c)}));
    cells.forEach(x => { if (x.c.scrollWidth > x.c.clientWidth + 2 && x.s.overflowX === 'visible') out.spill.push(x.c.textContent.trim().slice(0, 24)); });
    const grid = !out.stack && cells.some(x => parseFloat(x.s.borderLeftWidth) > 0 || parseFloat(x.s.borderRightWidth) > 0);
    out.grid = grid;
    if (grid) {
      const tb = t.getBoundingClientRect(), fr = (t.parentElement.closest('.dk-table,.tbl,.tw') || t).getBoundingClientRect();
      const L = Math.max(tb.left, fr.left), T = Math.max(tb.top, fr.top);
      const bw = (x, side) => x.s[`border${side}Style`] === 'none' ? 0 : parseFloat(x.s[`border${side}Width`]);
      cells.forEach(x => {
        // 왼쪽 안쪽 선
        if (x.b.left > L + 2) {
          if (!bw(x, 'Left')) {
            const nb = cells.filter(y => Math.abs(y.b.right - x.b.left) < 2 && Math.min(y.b.bottom, x.b.bottom) - Math.max(y.b.top, x.b.top) > 4);
            let cov = 0; nb.forEach(y => { if (bw(y, 'Right')) cov += Math.min(y.b.bottom, x.b.bottom) - Math.max(y.b.top, x.b.top); });
            if (cov < x.b.height - 4) out.gaps.push('세로선 ' + x.c.textContent.trim().slice(0, 16));
          }
        }
        if (x.b.top > T + 2) {
          if (!bw(x, 'Top')) {
            const nb = cells.filter(y => Math.abs(y.b.bottom - x.b.top) < 2 && Math.min(y.b.right, x.b.right) - Math.max(y.b.left, x.b.left) > 4);
            let cov = 0; nb.forEach(y => { if (bw(y, 'Bottom')) cov += Math.min(y.b.right, x.b.right) - Math.max(y.b.left, x.b.left); });
            if (cov < x.b.width - 4) out.gaps.push('가로선 ' + x.c.textContent.trim().slice(0, 16));
          }
        }
      });
    }
    res.tables.push(out);
  });
  return res;
}"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--widths', default='320,390,600,768,1024,1440')
    ap.add_argument('--browsers', default='chrome,webkit')
    ap.add_argument('--shots')
    ap.add_argument('--allow-scroll', default='compare', help='가로 스크롤을 허용하는 감싸개 클래스(쉼표)')
    a = ap.parse_args()
    widths = [int(w) for w in a.widths.split(',')]
    allow = [c for c in a.allow_scroll.split(',') if c]
    fails = 0
    with sync_playwright() as p:
        for bname in a.browsers.split(','):
            b = p.chromium.launch(channel='chrome') if bname == 'chrome' else p.webkit.launch()
            for f in a.files:
                url = Path(f).resolve().as_uri()
                for w in widths:
                    pg = b.new_page(viewport={'width': w, 'height': 900})
                    pg.goto(url); pg.wait_for_timeout(700)
                    r = pg.evaluate(AUDIT)
                    probs = []
                    if r['page'] > 1: probs.append(f'페이지 가로 넘침 {r["page"]}px')
                    for t in r['tables']:
                        if t['clip'] and not any(c in (t.get('clipCls') or '') for c in allow): probs.append(f'표{t["i"]} 잘림 {t["clip"]}px')
                        if t['gaps']: probs.append(f'표{t["i"]} 선 끊김 {len(t["gaps"])}곳 ({t["gaps"][0]})')
                        if t['spill']: probs.append(f'표{t["i"]} 칸 넘침 {len(t["spill"])}곳')
                    tag = f'{bname} {w}px {Path(f).parent.name}/{Path(f).name}'
                    if probs:
                        fails += 1; print('FAIL', tag, '·', '; '.join(probs[:4]), flush=True)
                        if a.shots:
                            Path(a.shots).mkdir(parents=True, exist_ok=True)
                            pg.screenshot(path=str(Path(a.shots) / f'{bname}-{w}-{Path(f).parent.name}.png'), full_page=True)
                    else:
                        print('PASS', tag, f'· 표 {len(r["tables"])}개' + (' (쌓음 ' + str(sum(t["stack"] for t in r["tables"])) + ')' if any(t["stack"] for t in r["tables"]) else '') + (f' · 원본 설계로 건너뜀 {r["skipped"]}' if r.get('skipped') else ''), flush=True)
                    pg.close()
            b.close()
    print('TABLES_OK' if not fails else f'TABLES_FAIL {fails}')
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
