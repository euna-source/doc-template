"""부품(kit): 아무 HTML에 붙이고 떼기 — 원본 보존·바꿔 끼우기·떼면 바이트 동일·자료 안전·엔진 펜스."""
import json, re, subprocess, sys, tempfile
from pathlib import Path
from doc_template import modules as M
from doc_template.render import render

page = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>손으로 만든 페이지</title>'
        '<style>body{font-family:serif;background:#fafafa}.cal{display:grid}</style></head>'
        '<body><header><h1>명예의 전당 운영 정책</h1></header><main><p>1회차 집계는 14일입니다.</p><p>2회차가 곧바로 이어집니다.</p></main></body></html>')
ids = [m['id'] for m in M.catalog()]
assert {'look', 'toggle', 'history', 'sources', 'verdict'} <= set(ids), ids
data = {'history': {'versions': [{'version': '1.1', 'date': '2026-10-17', 'changes': [{'type': 'new', 'text': '2회차 안내', 'target': '2회차가 곧바로'}]}]},
        'sources': {'sources': [{'title': '운영 기록 </script><script>alert(1)</script>', 'url': 'https://ex.com', 'state': '확인'}]}}
one = M.apply(page, ['look', 'toggle', 'history', 'sources'], data)
body = lambda h: re.sub(r'<!--doc-template-kit:start ([a-z0-9-]+)-->.*?<!--doc-template-kit:end \1-->', '', h, flags=re.S)
assert body(one) == page, '표식 사이를 빼면 원본과 같아야 한다(원본 구조 무변경)'
assert M.remove(one) == page, '떼면 원본과 바이트까지 같다'
two = M.apply(one, ['look', 'toggle', 'history', 'sources'], data)
assert two == one, '다시 붙이면 같은 결과(바꿔 끼움)'
assert one.count('<script data-dk="history">') == 1
assert '</script><script>alert(1)' not in one, '자료 안의 </script>는 태그를 닫지 않는다'
part = M.remove(one, ['history'])
assert 'data-dk="history"' not in part and 'data-dk="sources"' in part and 'name="generator" content="doc-template kit"' in part
assert M.remove(part) == page
assert 'name="generator" content="doc-template kit"' in one, '배포가 알아보는 생성기 표식'
for bad, msg in ((lambda: M.apply(page, ['nope']), '없는 부품'), (lambda: M.apply(page, ['history']), '자료가 필요'),
                 (lambda: M.apply('<p>조각</p>', ['look']), '<head>')):
    try: bad(); raise AssertionError(msg)
    except ValueError as e: assert msg in str(e), e
# verdict는 any에도 쓸 수 있게 선언돼 있다 → CSS만 붙는다
v = M.apply(page, ['verdict']); assert '.dk-verdict' in v
# 엔진 원고: ```verdict 펜스 → 세 칸, CSS는 쓸 때만
md = '---\ntitle: t\n---\n## 결론 | 지금 셀 수 있는 것은 둘이다\n\n```verdict\n확정 | 링크를 누른 횟수 | 사람 수 아님\n추정 | 새로 설치 | iOS는 추정 연결\n불가 | 웹에만 머문 사람\n```\n'
h, _ = render(md); assert h.count('<section class="v-') == 3 and '.dk-verdict{' in h and '<h4>확정</h4>' in h and 'iOS는 추정 연결' in h
h2, _ = render('---\ntitle: t\n---\n## 가 | 판정 없음\n\n본문\n'); assert '.dk-verdict{' not in h2, '안 쓰면 CSS도 없다'
# CLI
t = Path(tempfile.mkdtemp()); (t / 'p.html').write_text(page); (t / 'h.json').write_text(json.dumps(data['history']))
r = subprocess.run([sys.executable, '-m', 'doc_template.cli', 'kit', 'apply', str(t / 'p.html'), '-o', str(t / 'o.html'), '--with', 'look,history', '--data', f'history={t / "h.json"}'], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
r = subprocess.run([sys.executable, '-m', 'doc_template.cli', 'kit', 'remove', str(t / 'o.html'), '-o', str(t / 'back.html')], capture_output=True, text=True)
assert (t / 'back.html').read_text() == page
# 스크립트 안의 </head>·</body> 글자, 원본의 비슷한 주석, CRLF 줄끝
tricky = ('<!doctype html>\r\n<html><head>\r\n<script>var s="</head></body>";</script>\r\n<!--dk:start look--><p>예시</p><!--dk:end look-->\r\n</head>\r\n'
          '<body>\r\n<p>본문</p>\r\n<script>document.write("</body>")</script>\r\n</body></html>\r\n')
k = M.apply(tricky, ['look', 'toggle'])
assert 'var s="</head></body>";' in k and k.index('<style data-dk="look">') > k.index('var s=') and k.index('<script data-dk="toggle">') > k.index('document.write'), '진짜 태그 자리에만'
assert M.remove(k) == tricky and '<!--dk:start look--><p>예시</p>' in M.remove(k), '원본의 비슷한 주석은 남긴다'
(t / 'crlf.html').write_bytes(tricky.encode())
subprocess.run([sys.executable, '-m', 'doc_template.cli', 'kit', 'apply', str(t / 'crlf.html'), '-o', str(t / 'crlf-k.html'), '--with', 'look'], check=True, capture_output=True)
subprocess.run([sys.executable, '-m', 'doc_template.cli', 'kit', 'remove', str(t / 'crlf-k.html'), '-o', str(t / 'crlf-b.html')], check=True, capture_output=True)
assert (t / 'crlf-b.html').read_bytes() == tricky.encode(), 'CRLF까지 바이트 동일'
# MCP 떼기는 원본을 덮지 않는다
from doc_template import mcp_server as S
(t / 'k.html').write_text(M.apply(page, ['look']))
r = S.remove_modules(str(t / 'k.html')); assert r['path'].endswith('k-plain.html') and 'data-dk="look"' in (t / 'k.html').read_text()
try: S.remove_modules(str(t / 'h.json')); raise AssertionError('html만')
except ValueError: pass
print('PASS kit: 원본 보존, 떼면 동일, 바꿔 끼움, 자료 안전, 엔진 펜스, CLI')
