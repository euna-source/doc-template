"""한국어 문체 점검(ko-*): 몰린 패턴은 제안으로 잡고, 평범한 문장·코드 안 글자는 잡지 않는다."""
from doc_template.lint import review
base = '---\ntitle: t\nobi:\n  text: 결론\n---\n## 배경 | 왜 지금 하는가를 한 문장으로\n'
bad = base + ('이 문제에 있어서 판단되어진다. 단순한 기능을 넘어 경험이다. 이는 시사하는 바가 크다. 크게 세 가지로 나눌 수 있다. '
              '지금이 바꿀 때입니다. 결론적으로 좋다. 요약하면 좋다. 정리하자면 좋다. 이를 통해 좋다. '
              '좋다는 것이다. 맞다는 것이다. 된다는 뜻이다. 사용자 경험(User Experience)과 사용자 경험(User Experience)\n')
ids = {i['id'] for i in review(bad)['issues']}
for k in ('ko-double-passive', 'ko-beyond', 'ko-significance', 'ko-enum-intro', 'ko-thats-it', 'ko-summary-words', 'ko-paren-english'):
    assert k in ids, (k, ids)
assert all(i['level'] == '제안' for i in review(bad)['issues'] if i['id'].startswith('ko-'))
good = base + '발표될 때입니다. 열어 보지 않는 파일에 있어서 오래 남았습니다. 포스터 QR로 들어온 사람을 셉니다. 안드로이드는 확정하고 iOS는 추정합니다. 대표님이 B안을 고르면 다음 주에 붙입니다.\n\n```\n판단되어진다 에 있어서\n```\n'
assert not {i['id'] for i in review(good)['issues'] if i['id'].startswith('ko-')}, review(good)['issues']
commas = base + '보고, 듣고, 쓰고, 읽고, 말하며, 생각하지만, 걸으면서, 먹고, 끝낸다.\n'
assert 'ko-comma-after-connective' in {i['id'] for i in review(commas)['issues']}
print('PASS ko-style: 몰린 패턴 제안, 평문·코드 무시')
