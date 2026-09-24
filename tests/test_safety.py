"""회귀 시험: HTML 주입·경로 이탈·덮어쓰기·배포 파일 검증. 사용: .venv/bin/python tests/test_safety.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from doc_template.render import render
from doc_template import mcp_server as M
from doc_template.publish import _check_html, _slug
fails = []
def expect(name, cond):
    if not cond: fails.append(name)
def raises(fn):
    try: fn(); return False
    except Exception: return True
md = "---\ntitle: <script>alert(1)</script>\nobi:\n  text: <img src=x onerror=alert(2)>\n---\n## <img src=x onerror=alert(3)> | <b>x</b>\n\n본문 <script>alert(4)</script> [링크](javascript:alert(5))\n"
html, _ = render(md)
body = html.split('<body>', 1)[1].split('<script>\n', 1)[0]
expect('주입: script 태그 없음', '<script>alert' not in body)
expect('주입: img 태그 실행 없음', '<img src=x' not in body and '<b>x</b>' not in body)
expect('주입: javascript 링크 없음', 'href="javascript:' not in body)
expect('starter 경로 이탈 차단', raises(lambda: M.get_starter('../../../etc/passwd')))
d = Path(tempfile.mkdtemp()); f = d / 'a.html'; f.write_text('x')
expect('덮어쓰기 차단', raises(lambda: M.render_document('# t', output_path=str(f))))
expect('html 아닌 출력 차단', raises(lambda: M.render_document('# t', output_path=str(d / 'a.txt'))))
ok = M.render_document('# t', output_path=str(d / 'b.html')); expect('정상 출력', Path(ok['path']).exists())
expect('덮어쓰기 허용 옵션', Path(M.render_document('# t', output_path=str(d / 'b.html'), overwrite=True)['path']).exists())
expect('render_file .md만', raises(lambda: M.render_file(str(f))))
expect('배포: 생성기 표식 없는 파일 거부', raises(lambda: _check_html(f)))
expect('배포: 우리 파일 통과', _check_html(ok['path']))
expect('배포: 이상한 slug 거부', raises(lambda: _slug('../..')))
print('fails:', fails or 0); sys.exit(1 if fails else 0)
