"""부품을 붙인 페이지를 실제 브라우저로: 버튼·서랍·바뀐 곳 형광·다크 전환·출처 트레이·휴대폰 폭·오류 없음."""
import json, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
from doc_template import modules as M
page = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>t</title>'
        '<style>body{margin:0 auto;max-width:720px;padding:24px;font-family:serif}</style></head><body><h1>운영 정책</h1><p>1회차 집계는 14일입니다.</p><p>2회차가 곧바로 이어집니다.</p><picture><img alt="그림" src="data:image/gif;base64,R0lGODlhAQABAAAAACw="></picture></body></html>')
data = {'history': {'versions': [{'version': '1.1', 'changes': [{'type': 'new', 'text': '2회차', 'target': '2회차가 곧바로'}, {'type': 'mod', 'text': '집계 기간', 'target': '14일'}]}]},
        'sources': {'sources': [{'title': '기록', 'url': 'https://ex.com', 'state': '일부', 'note': '10/16'}]}}
f = Path(tempfile.mkdtemp()) / 'k.html'; f.write_text(M.apply(page, ['look', 'toggle', 'history', 'sources'], data))
fails = []
def ok(c, m): print(('PASS ' if c else 'FAIL ') + m); c or fails.append(m)
with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome')
    for w in (1280, 390):
        pg = b.new_page(viewport={'width': w, 'height': 800}); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(f.as_uri()); pg.wait_for_timeout(300)
        ok('Pretendard' in pg.evaluate('getComputedStyle(document.body).fontFamily'), f'{w}: 룩 — 서체')
        ok(pg.locator('mark.dk-chg').count() == 0, f'{w}: 바뀐 곳 형광은 기본 꺼짐')
        pg.click('.dk-hbtn'); ok(pg.locator('.dk-hpanel').is_visible(), f'{w}: 버전 기록 서랍 열림')
        pg.check('.dk-show'); ok(pg.locator('mark.dk-chg[data-type=new]').count() == 1 and pg.locator('mark.dk-chg[data-type=mod]').count() == 1, f'{w}: 바뀐 곳 형광 신규·수정')
        pg.uncheck('.dk-show'); ok(pg.locator('mark.dk-chg').count() == 0 and pg.inner_text('body').count('2회차가 곧바로') == 1, f'{w}: 끄면 원래 글자 그대로')
        pg.keyboard.press('Escape'); ok(pg.locator('.dk-hpanel').is_hidden(), f'{w}: Esc로 닫힘')
        pg.click('.dk-tog'); ok('dk-invert' in pg.evaluate('document.documentElement.className'), f'{w}: 자체 다크 없는 페이지는 반전으로 다크')
        ok(pg.evaluate("getComputedStyle(document.querySelector('picture')).filter") == 'none' and 'invert' in pg.evaluate("getComputedStyle(document.querySelector('picture img')).filter"), f'{w}: picture 안 그림은 한 번만 되돌림')
        pg.emulate_media(media='print'); ok(pg.evaluate("getComputedStyle(document.documentElement).filter") == 'none' and pg.evaluate("getComputedStyle(document.querySelector('img')).filter") == 'none', f'{w}: 다크로 인쇄해도 반전 없음'); pg.emulate_media(media='screen')
        pg.click('.dk-tog'); ok('dk-invert' not in pg.evaluate('document.documentElement.className'), f'{w}: 다시 누르면 라이트')
        ok(pg.inner_text('.dk-src summary') == '출처 · 1', f'{w}: 출처 트레이')
        ok(pg.evaluate('document.documentElement.scrollWidth') <= w, f'{w}: 가로 넘침 없음')
        ok(not errs, f'{w}: 페이지 오류 없음 {errs[:1]}')
    b.close()
print(json.dumps({'fails': fails}, ensure_ascii=False))
