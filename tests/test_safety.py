"""회귀 시험: HTML 주입·경로 이탈·덮어쓰기·배포 파일 검증. 사용: .venv/bin/python tests/test_safety.py"""
import os, sys, tempfile
os.environ.pop('DOC_TEMPLATE_JIRA', None)  # 시험은 환경 변수와 무관하게
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
body = html.split('<body', 1)[1].split('>', 1)[1].split('<script>\n', 1)[0]
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
from doc_template.lint import review
good = review(open(Path(__file__).resolve().parents[1] / 'src/doc_template/assets/starters/plan.md').read())
expect('구조: 시작 문서는 경고 없음', not [i for i in good['issues'] if i['level'] == '경고'])
mixed = "---\nobi:\n  text: 결론\n---\n## 배경 | 왜 필요한가를 말한다\n\n" + ('API 배치 DB 엔드포인트 설명 ' * 60) + "\n\n## 부록 | 문안\n\n" + ('참가자 안내 문안 ' * 80)
ids = {i['id'] for i in review(mixed)['issues']}
expect('구조: 개발 상세 섞임 경고', 'audience-mix' in ids)
expect('구조: 부록 문안 경고', 'appendix-content' in ids)
expect('구조: 강조 과다 경고', 'mark-many' in {i['id'] for i in review('## 가 | 결론 문장입니다\n\n==a== ==b==')['issues']})
# 결정 모음: 접이 상자·표지 줄 수·관련 절 링크·절 머리 표시, 주입 차단
dm = ("---\npending: 남은 {n}가지\nobi:\n  text: 결론\n---\n## 선정 기준 | 무엇으로 뽑나를 말한다\n\n본문\n\n"
      "## 결정할 것 | 정할 두 가지를 모은다\n\n> [!decide]- 첫 질문 <img src=x onerror=alert(6)>\n> 배경 문장\n> 관련: [[#선정 기준]]\n\n"
      "> [!decide]- 둘째 질문\n> 배경\n> 관련: [[#없는 절]]\n")
dh, dr = render(dm)
expect('결정: 항목 수', dr['decisions'] == 2 and dh.count('<details class="callout decide"') == 2)
expect('결정: 표지 줄 문구와 수', '남은 2가지' in dh and 'class="pending"' in dh)
expect('결정: 관련 절 링크', '<a class="xref" href="#s1">선정 기준</a>' in dh)
expect('결정: 없는 절은 글자만', '없는 절' in dh and '[[#' not in dh)
expect('결정: 절 머리 표시', '<a class="sec-pending" href="#d1">정할 것 1</a>' in dh)
expect('결정: 관련 줄 분리', '<p class="rel">관련:' in dh)
expect('결정: 주입 없음', '<img src=x' not in dh.split('<body', 1)[1].split('>', 1)[1])
xm = ("## R&D | 연구 개발을 말한다\n\n본문 [[#R&D]] 과 [[#R&D 폐기안]]\n\n```\n[[#R&D]]\n```\n\n## 선정 기준 | 무엇으로 뽑나를 말한다\n\n[[#선정]]\n")
xh, _ = render(xm)
expect('링크: 특수문자 절', '<a class="xref" href="#s1">R&amp;D</a>' in xh)
expect('링크: 앞부분만 같은 이름은 잇지 않음', 'href="#s1">R&amp;D 폐기안' not in xh and 'R&amp;D 폐기안' in xh)
expect('링크: 코드 안은 그대로', '[[#R&amp;D]]' in xh)
expect('링크: 접두어로 잇지 않음', 'href="#s2">선정<' not in xh)
lm = ("---\njira: https://example.atlassian.net\ncode: CCO-121 · v2.14\nmeta:\n  상위 문서: CCO-121, CCQ-45\n  관련: '[일정표](https://example.com/p) [나쁜](javascript:alert(1)) <b>x</b>'\n  읽는 사람: 대표\n---\n## 가 | 결론 문장입니다\n")
lh, lr = render(lm)
expect('링크: 머리 티켓', '<a href="https://example.atlassian.net/browse/CCO-121" target="_blank" rel="noopener">CCO-121</a> · v2.14' in lh)
expect('링크: 메타 티켓 둘', lh.count('/browse/CCQ-45') == 1 and lh.count('/browse/CCO-121') == 2)
expect('링크: 메타 마크다운 링크', '<a href="https://example.com/p" target="_blank" rel="noopener">일정표</a>' in lh)
expect('링크: javascript·태그 차단', 'href="javascript' not in lh and '<b>x</b>' not in lh)
expect('링크: jira 없으면 글자만', 'browse' not in render("---\ncode: CCO-121\n---\n## 가 | 결론 문장입니다\n")[0])
expect('구조: 읽는 사람 메타 제안', 'meta-reader' in {i['id'] for i in lr['structure_issues']})
expect('상태: 안 적으면 표시 없음', '<dt>상태</dt>' not in render('---\ntitle: t\n---\n## 가 | 결론 문장입니다\n')[0] and '<dt>상태</dt>' in render('---\nstatus: review\n---\n## 가 | 결론 문장입니다\n')[0])
bh = render("---\njira: https://example.atlassian.net\n---\n## 가 | 결론 문장입니다\n\n본문 CCO-7 과 [이미 링크 CCO-8](https://x.com) `CCQ-9`\n")[0]
expect('본문 티켓 링크', 'href="https://example.atlassian.net/browse/CCO-7"' in bh and '/browse/CCO-8' not in bh and '/browse/CCQ-9' not in bh)
kh = render("---\njira: https://example.atlassian.net\nmeta:\n  관련: '[계획](https://example.com/Plan_(draft)) 참고'\n---\n## 가 | 결론 문장입니다\n\nCCO-121은 정본이고 CCQ-45를 봅니다. abc/CCO-9 와\n")[0]
expect('티켓: 조사 붙어도 링크', '/browse/CCO-121"' in kh and '/browse/CCQ-45"' in kh)
expect('티켓: 경로·단어 안은 무시', '/browse/CCO-9"' not in kh)
expect('링크: 괄호 든 주소', 'href="https://example.com/Plan_(draft)"' in kh)
os.environ['DOC_TEMPLATE_JIRA'] = 'https://env.atlassian.net'
eh = render("---\ncode: CCO-3\n---\n## 가 | 결론 문장입니다\n")[0]; fh = render("---\njira: https://fm.atlassian.net\ncode: CCO-3\n---\n## 가 | 결론 문장입니다\n")[0]
os.environ.pop('DOC_TEMPLATE_JIRA')
expect('티켓: 환경 변수 주소', 'https://env.atlassian.net/browse/CCO-3' in eh)
expect('티켓: 머리말이 환경 변수보다 먼저', 'https://fm.atlassian.net/browse/CCO-3' in fh and 'env.atlassian' not in fh)
lint_ids = {i['id'] for i in review("## 배경 | 왜 필요한가를 말한다\n\n이 기획은 순위로 행동을 이끄는 방식을 택합니다. 값 {{가안}} {{확정}} {{확인 필요}}\n")['issues']}
expect('구조: 이름표 흩어짐 경고', 'inline-tags' in lint_ids)
expect('구조: 제삼자 말투 제안', 'narrator' in lint_ids)
expect('구조: 대안 판정 이름표는 허용', 'inline-tags' not in {i['id'] for i in review('## 대안 | 둘 중 B를 고른다\n\n| 안 | 판단 |\n|---|---|\n| B | {{추천}} |\n')['issues']})
# 일정표형: 국면·달력·두 열·서랍·변경 비교(꼬리 보존)·주입 차단
from doc_template import components as C
sm = (ROOT_ := Path(__file__).resolve().parents[1] / 'src/doc_template/assets/starters/schedule.md').read_text()
sh, _ = render(sm)
expect('일정: 날짜 칸 16개', sh.count('class="day') == 16)
expect('일정: 날짜 칸이 흐름 줄로', 'href="#d1007" data-date="2026-10-08"' in sh and 'id="d1006"' in sh)
expect('일정: 두 열', sh.count('class="col col-timeline"') == 2 and sh.count('class="col col-cards"') == 2)
expect('일정: 서랍 2개와 버튼', sh.count('class="drawer"') == 2 and 'data-layer="' in sh)
expect('일정: 신호 카드 모양', 'class="card core"' in sh and 'class="card warn"' in sh and 'class="card red"' in sh)
xh, _ = render("---\ntemplate: schedule\n---\n## 가 | 결론 문장입니다\n\n> [!note]- 1\n> - **곳**: 이전 「<img src=x onerror=alert(1)>A」 → 이후 「B」 (꼬리 말)\n")
expect('일정: 비교 꼬리 보존', '꼬리 말' in xh and 'class="chg"' in xh)
expect('일정: 비교 주입 없음', '<img src=x' not in xh.split('<body', 1)[1])
expect('일정: 겹친 괄호', C._split_pair('이전 「A 「x」 B」 → 이후 「C」 끝')[1:] == ('A 「x」 B', 'C', ' 끝'))
# 목록형: 표·필터 속성·접힘·열 묶음·주입
cm = (Path(__file__).resolve().parents[1] / 'src/doc_template/assets/starters/catalog.md').read_text()
ch, _ = render(cm)
expect('목록: 행 2개', ch.count('<tr class="row') == 2)
expect('목록: 필터 속성', 'data-f-묶음="현행"' in ch and 'data-field="갱신"' in ch)
expect('목록: 보관 그룹 없음 → 접힘 아님', 'data-fold="0"' in ch)
expect('목록: 열 묶음 머리줄', 'class="hg"' in ch and 'data-span-core=' in ch)
expect('목록: 열 설명 버튼이 서랍으로', 'class="qh" data-layer="' in ch)
ih, _ = render("---\ntemplate: catalog\ncatalog: {section: 목록, columns: [내용]}\n---\n## 목록 | 목록\n\n### 01 그룹\n\n#### #1 <script>x</script>\n\n- 내용: <img src=x onerror=alert(2)>\n")
expect('목록: 주입 없음', '<script>x' not in ih.split('<body', 1)[1].split('<script>\n', 1)[0] and '<img src=x' not in ih)
bh2 = render("---\ntitle: t\n---\n## 가 | 결론 문장입니다\n\n본문은 **잠금 상태(OS·기기)**와 **{활동명}**님이 `**코드**`\n")[0]
expect('한글 조사 앞 굵게', '<strong>잠금 상태(OS·기기)</strong>와' in bh2 and '<strong>{활동명}</strong>님이' in bh2 and '<code>**코드**</code>' in bh2)
expect('한글 굵게: 특수문자 한 번만', '<strong>A&amp;B</strong>와' in render("---\ntitle: t\n---\n## 가 | 결론 문장입니다\n\n**A&B**와\n")[0])
print('fails:', fails or 0); sys.exit(1 if fails else 0)
