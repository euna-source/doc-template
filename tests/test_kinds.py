"""문서 템플릿 모음 유형 렌더러(doc_template.kinds): 여섯 유형 렌더, prd 이름, 허용 함수 호출, CLI JSON 오류."""
import json, subprocess, sys
from doc_template.kinds import call
from doc_template.kinds.render import render, KINDS

md = '# 제목 — 한 줄\n- 상태: 진행\n- 버전: 1.0\n\n> 결론\n\n## 안건 — 질문\n본문 **굵게**  \n둘째 줄\n\n## 출처\n- 하나\n'
for k in KINDS:
    h = render(md, k)
    assert h.startswith('<!doctype html>'), k
    assert '제목' in h, k
assert 'class="t-plan"' in render(md, 'prd')  # 화면 표지는 옛 키 그대로(결과 보존)
try:
    render(md, 'plan'); raise AssertionError('plan은 거절해야 한다')
except ValueError as e:
    assert 'prd' in str(e)
assert render(md, 'prd', standalone=False).startswith('<div class="shell">')
assert 'meeting-copy-data' in render(md, 'minutes', transcript='원문', canonical_url='https://ex.com/m/')
assert call('kinds') == list(KINDS)
assert 'mono' in call('themes') and 'c8' in call('themes')
try:
    call('open'); raise AssertionError('허용 목록 밖 함수는 거절')
except ValueError:
    pass
out = subprocess.run([sys.executable, '-m', 'doc_template.cli', 'kinds', 'call'], input=json.dumps({'fn': 'render', 'args': [md, 'plan']}).encode(), capture_output=True)
res = json.loads(out.stdout)
assert res['error']['type'] == 'ValueError', res
out = subprocess.run([sys.executable, '-m', 'doc_template.cli', 'kinds', 'call'], input=json.dumps({'fn': 'render', 'args': [md, 'pt']}).encode(), capture_output=True)
assert json.loads(out.stdout)['result'].startswith('<!doctype html>')
for bad in (b'{', b'[]', b'null', b'{"fn": 3}', b'{"fn": "render", "args": {}}', b'{"fn": "render", "kwargs": []}'):
    out = subprocess.run([sys.executable, '-m', 'doc_template.cli', 'kinds', 'call'], input=bad, capture_output=True)
    assert out.returncode == 0 and json.loads(out.stdout)['error']['type'] == 'ValueError', (bad, out.stdout, out.stderr[-200:])
print('PASS kinds: six kinds, prd name, allowlist, cli json error')
