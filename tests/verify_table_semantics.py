"""표 부품 의미 보존(실제 브라우저): 카드로 쌓았을 때 칸마다 붙는 이름표가 그 칸의 열 머리글과 맞는지 — rowspan="0"·rowspan·colspan·머리글 두 줄.
쓰기: uv run --with-editable . --with playwright python tests/verify_table_semantics.py  → 끝 줄 SEMANTICS_OK / SEMANTICS_FAIL n"""
import sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
from doc_template import modules as M

PAGE = '''<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:8px">
<div class="dk-table dk-frame"><table>
<thead><tr><th rowspan="2">역할</th><th colspan="2">기능</th><th rowspan="2">비고</th></tr><tr><th>이름</th><th>요구사항</th></tr></thead>
<tbody>
<tr><td rowspan="0">팀장</td><td>생성</td><td>이름·사진 입력</td><td>필수</td></tr>
<tr><td>관리</td><td>정보 수정</td><td>-</td></tr>
<tr><td>해체</td><td colspan="2">2주간 읽기 전용</td></tr>
</tbody>
<tbody><tr><td>팀원</td><td>합류</td><td>수락·거절</td><td>알림</td></tr></tbody>
</table></div></body></html>'''
# 칸 글자 → 붙어야 할 이름표(첫 칸은 제목이라 이름표 없음, 병합 묶음 칸은 묶음 머리)
WANT = {'이름·사진 입력': '기능 · 요구사항', '필수': '비고', '정보 수정': '기능 · 요구사항', '-': '비고', '2주간 읽기 전용': '기능 · 요구사항', '수락·거절': '기능 · 요구사항', '알림': '비고'}
TITLE = {'생성', '관리', '해체', '팀원'}
GROUP = {'팀장'}

def main():
    t = Path(tempfile.mkdtemp()) / 'sem.html'
    t.write_text(M.apply(PAGE, ['table']), encoding='utf-8')
    fails = 0
    with sync_playwright() as p:
        for name in ('chrome', 'webkit'):
            b = p.chromium.launch(channel='chrome') if name == 'chrome' else p.webkit.launch()
            pg = b.new_page(viewport={'width': 360, 'height': 900}); pg.goto(t.as_uri()); pg.wait_for_timeout(500)
            got = pg.evaluate("""()=>({stack:document.querySelector('.dk-table').classList.contains('dk-stack'),
              cells:[...document.querySelectorAll('tbody td')].map(c=>({t:c.textContent.trim(),l:c.getAttribute('data-dk-label')||'',title:c.classList.contains('dk-title'),grp:c.classList.contains('dk-grp')}))})""")
            probs = [] if got['stack'] else ['360px에서 카드로 쌓지 않음']
            for c in got['cells']:
                if c['t'] in GROUP and not c['grp']: probs.append(f"{c['t']}: 묶음 머리가 아님")
                elif c['t'] in TITLE and not c['title']: probs.append(f"{c['t']}: 줄 제목이 아님")
                elif c['t'] in WANT and c['l'] != WANT[c['t']]: probs.append(f"{c['t']}: 이름표 「{c['l']}」 ≠ 「{WANT[c['t']]}」")
            print(('FAIL ' if probs else 'PASS ') + name + ' 카드 이름표·제목·묶음 ' + '; '.join(probs[:5]), flush=True); fails += bool(probs)
            b.close()
    print('SEMANTICS_OK' if not fails else f'SEMANTICS_FAIL {fails}'); sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
