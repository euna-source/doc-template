"""일정표형·목록형 스타터를 4폭×2모드로 렌더해 넘침·스크립트 오류·12px 미만 글자·주요 조작을 검사한다.
사용: uv run --with playwright python tests/verify_types.py"""
import json, sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from doc_template.render import render

ROOT = Path(__file__).resolve().parents[1] / 'src' / 'doc_template' / 'assets' / 'starters'
tmp = Path(tempfile.mkdtemp()); fails = []; checks = 0
SMALL = '''() => { let n = 0; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const el = w.currentNode.parentElement; if (!w.currentNode.textContent.trim() || !el.offsetParent) continue;
    if (parseFloat(getComputedStyle(el).fontSize) < 12) n++; } return n; }'''
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    for kind in ('schedule', 'catalog'):
        html, _ = render((ROOT / f'{kind}.md').read_text()); f = tmp / f'{kind}.html'; f.write_text(html)
        for w in (1440, 1024, 390, 360):
            for mode in ('light', 'dark'):
                pg = b.new_page(viewport={'width': w, 'height': 900}, color_scheme=mode); errs = []
                pg.on('pageerror', lambda e: errs.append(str(e))); pg.goto(f.as_uri(), wait_until='networkidle')
                tag = f'{kind} {w} {mode}'
                checks += 3
                if errs: fails.append(f'{tag}: 스크립트 오류 {errs[:1]}')
                if pg.evaluate('document.documentElement.scrollWidth > innerWidth'): fails.append(f'{tag}: 가로 넘침')
                if pg.evaluate(SMALL): fails.append(f'{tag}: 12px 미만 글자 {pg.evaluate(SMALL)}곳')
                if kind == 'schedule':
                    checks += 2
                    pg.locator('.day').first.click(); pg.wait_for_timeout(900)
                    if not pg.evaluate("document.querySelector('.day.sel') !== null"): fails.append(f'{tag}: 날짜 칸 선택 표시 없음')
                    pg.locator('[data-layer]').first.click(); pg.wait_for_timeout(200)
                    if not pg.evaluate("!!document.querySelector('.drawer:not([hidden])')"): fails.append(f'{tag}: 서랍이 안 열림')
                    pg.keyboard.press('Escape')
                    # 서랍 안 항목 주소로 새로 열기
                    checks += 1
                    inner = pg.evaluate("(() => { const d = document.querySelector('.drawer'); const el = d.querySelector('[id]:not(.drawer)') || d.querySelector('h2'); return el ? el.id : '' })()")
                    if inner:
                        p2 = b.new_page(viewport={'width': w, 'height': 900}, color_scheme=mode)
                        p2.goto(f.as_uri() + '#' + inner, wait_until='networkidle')
                        if not p2.evaluate("!!document.querySelector('.drawer:not([hidden])')"): fails.append(f'{tag}: 서랍 안 주소로 열 때 서랍이 안 열림')
                        p2.close()
                else:
                    checks += 2
                    c0 = pg.inner_text('#cat-count')
                    pg.evaluate("document.querySelector('.fgroup[data-field=\"갱신\"] button[data-v=\"all\"]').click()")
                    if pg.inner_text('#cat-count') == c0: fails.append(f'{tag}: 필터가 건수를 안 바꿈')
                    pg.fill('#cat-q', 'zzzz')
                    if not pg.inner_text('#cat-count').startswith('표시 0'): fails.append(f'{tag}: 검색이 안 걸러짐')
                    # 접기 → 검색 → 초기화: 손으로 접은 그룹도 검색하면 보이고 초기화하면 처음 상태로
                    checks += 2
                    pg.fill('#cat-q', '')
                    pg.evaluate("document.querySelector('.gtog').click()")
                    pg.fill('#cat-q', '첫 항목')
                    if not pg.evaluate("[...document.querySelectorAll('tr.row')].some(r => !r.classList.contains('hidden') && r.offsetParent)"): fails.append(f'{tag}: 접은 그룹이 검색에 안 보임')
                    pg.evaluate("document.getElementById('cat-reset').click()")
                    if pg.inner_text('#cat-count') != c0: fails.append(f'{tag}: 초기화가 처음 건수로 안 돌아감')
                    # 필터 하나 고른 뒤 없는 검색어 → '다른 필터 풀기'로 빈 결과에서 벗어나야 한다
                    checks += 1
                    pg.evaluate("document.querySelector('.fgroup button[data-v]:not([data-v=all]):not([data-v=any])').click()")
                    pg.fill('#cat-q', 'zzzz')
                    pg.evaluate("document.querySelector('.empty-fix').click()")
                    if pg.inner_text('#cat-count').startswith('표시 0'): fails.append(f'{tag}: 다른 필터 풀기로 빈 결과를 못 벗어남')
                    pg.evaluate("document.getElementById('cat-reset').click()")
                pg.close()
    b.close()
print(json.dumps({'checks': checks, 'fails': fails}, ensure_ascii=False, indent=1))
sys.exit(1 if fails else 0)
