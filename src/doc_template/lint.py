"""문서 구조 점검 — assets/guide.md의 원칙을 기계적으로 확인한다.
각 지적은 {id, level(경고|제안), where, message, fix}. 점수는 100에서 경고 8점·제안 3점씩 뺀다."""
import re
import yaml

APPENDIX = ('출처', '변경 이력', '부록', '출처·이력')
LIMITS = dict(obi=90, deck=120, sec_chars=600, body_chars=3000, table_rows=8, para=300, marks_total=3, name=10)


def _plain(md):
    md = re.sub(r'```.*?```', '', md, flags=re.S)
    md = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', md)
    md = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', md)
    md = re.sub(r'[=*_`>#|{}\-]', '', md)
    return re.sub(r'\s+', ' ', md).strip()


def _folded(md):
    """접이 상자(> [!x]- 제목)의 펼친 내용은 처음 읽을 때 보이지 않으므로 분량에서 뺀다. 제목 줄은 남긴다."""
    out, skip = [], False
    for line in md.splitlines():
        if re.match(r'^>\s*\[!\w+\]-', line) or (re.match(r'^>\s*\[!decide\]', line, re.I)):
            out.append(line); skip = True; continue
        if skip and line.startswith('>'):
            continue
        skip = False; out.append(line)
    return '\n'.join(out)


TAG = re.compile(r'\{\{[^}]+\}\}')
VERDICT = re.compile(r'\{\{\s*(추천|보류|채택|기각|채택 제안|불채택)\s*\}\}')  # 대안 비교표의 판정은 이름표로 둔다
# 쓰는 사람이 자기 문서를 남의 일처럼 설명하는 말투: '이 기획은 … 택합니다'
NARRATE = re.compile(r'(?:^|[.!?]\s+)이\s*(?:기획|문서|안|제안)[은는이가]\s[^.\n]{0,80}?(?:택합니다|다룹니다|제안합니다|목표로\s*합니다|합니다)\.', re.M)


def review(md_text):
    issues = []
    add = lambda i, lvl, where, msg, fix: issues.append(dict(id=i, level=lvl, where=where, message=msg, fix=fix))
    fm, body = {}, md_text
    m = re.match(r'^---\n(.*?)\n---\n?(.*)$', md_text, re.S)
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            add('frontmatter', '경고', '머리말', '머리말(YAML)을 읽지 못했습니다.', '들여쓰기와 따옴표를 확인하세요.')
        body = m.group(2)

    # 1. 결론을 맨 위에
    obi = fm.get('obi') or {}
    if not obi.get('text'):
        add('obi-missing', '경고', '띠지', '결론(띠지) 한 문장이 없습니다.', 'obi.text에 결론이나 제안을 한 문장으로 쓰세요.')
    else:
        n = len(str(obi['text']))
        if n > LIMITS['obi']:
            add('obi-long', '제안', '띠지', f'띠지 결론이 {n}자입니다.', f"{LIMITS['obi']}자 안으로 줄여 한 번에 읽히게 하세요.")
        cells = obi.get('cells') or []
        if len(cells) != 3:
            add('obi-cells', '제안', '띠지', f'띠지 칸이 {len(cells)}개입니다.', '무엇이 바뀌나 · 감수할 대가 · 뒤집힐 조건 세 칸을 쓰세요.')
    for k in (fm.get('meta') or {}):
        if re.search(r'읽는\s*사람|독자|대상', str(k)):
            add('meta-reader', '제안', '메타', f"메타의 「{k}」는 쓰는 사람만 알면 되는 정보입니다.", '빼고, 그 자리에 상위 문서(예: 상위 문서: CCO-121)를 두세요.')
    deck = str(fm.get('deck', ''))
    if not deck:
        add('deck-missing', '제안', '덱', '표지 요약(deck)이 없습니다.', '무엇을 결정하는 문서인지 두 문장으로 쓰세요.')
    elif len(deck) > LIMITS['deck']:
        add('deck-long', '제안', '덱', f'덱이 {len(deck)}자입니다.', f"{LIMITS['deck']}자 안으로 줄이세요.")

    # 절 나누기
    parts = re.split(r'^##\s+(.+)$', body, flags=re.M)
    sections = [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts), 2)]
    main = [(h, b) for h, b in sections if not h.split('|')[0].strip().startswith(APPENDIX)]
    appx = [(h, b) for h, b in sections if h.split('|')[0].strip().startswith(APPENDIX)]
    if not 4 <= len(main) <= 9:
        add('sec-count', '제안', '문서', f'본문 절이 {len(main)}개입니다.', '5~8개로 묶거나 나누세요.')

    total, marks_total = 0, 0
    for h, b in main:
        name, _, head = h.partition('|')
        name, head = name.strip(), head.strip()
        where = f'「{name}」'
        # 2. 소제목만 읽어도
        if not head:
            add('head-missing', '경고', where, '소제목이 없습니다. 목차 이름만으로는 절의 결론을 알 수 없습니다.', '## 이름 | 이 절의 결론을 문장으로')
        elif head == name or len(head) < 6:
            add('head-weak', '제안', where, f'소제목 「{head}」이 결론을 말하지 않습니다.', '이 절에서 읽는 사람이 가져갈 한 문장을 소제목으로 쓰세요.')
        if len(name) > LIMITS['name']:
            add('name-long', '제안', where, f'목차 이름이 {len(name)}자입니다.', f"{LIMITS['name']}자 안의 짧은 명사로 쓰세요.")
        # 4. 한 문서 한 독자
        chars = len(_plain(_folded(b))); total += chars
        if chars > LIMITS['sec_chars']:
            add('sec-long', '경고', where, f'절 분량이 {chars}자입니다.', '다른 독자(개발 상세·참가자 문안)를 위한 내용이면 별도 문서로 떼고 링크만 두세요.')
        if re.search(r'API|배치|엔드포인트|어드민|스키마|쿼리|DB', b) and chars > 400:
            add('audience-mix', '경고', where, '개발 상세가 섞여 있습니다.', '결정에 필요한 요지만 남기고 구현 상세는 개발 요건 문서로 옮기세요.')
        # 5. 형식
        for tb in re.findall(r'((?:^\|.*\|\s*$\n?)+)', b, flags=re.M):
            rows = [r for r in tb.strip().splitlines() if not re.match(r'^\|\s*:?-', r)]
            if len(rows) - 1 > LIMITS['table_rows']:
                add('table-long', '제안', where, f'표가 {len(rows) - 1}행입니다.', f"{LIMITS['table_rows']}행 안으로 줄이거나 두 표로 나누세요.")
        for para in re.split(r'\n\s*\n', b):
            p = para.strip()
            if p and not p.startswith(('|', '-', '>', '```', '#', '!')) and len(_plain(p)) > LIMITS['para']:
                add('para-long', '제안', where, f'한 문단이 {len(_plain(p))}자입니다.', f"{LIMITS['para']}자 안으로 나누세요.")
        # 6. 강조
        mk = len(re.findall(r'==.+?==', b)); marks_total += mk
        if mk > 1:
            add('mark-many', '경고', where, f'한 절에 강조가 {mk}곳입니다.', '가장 먼저 읽혀야 할 한 구절만 남기세요.')
        # 8. 다음 행동
        if re.search(r'다음\s*행동|할\s*일|액션', name):
            for t in re.findall(r'^- \[[ /xX]\]\s*(.+)$', b, flags=re.M):
                if t.strip().startswith('[x]'):
                    continue
                if '@' not in t or '~' not in t:
                    add('action-owner', '제안', where, f'「{t[:24]}…」에 담당이나 기한이 없습니다.', '@담당 ~기한을 붙이세요.')

        # 9. 이름표는 본문에 흩지 않는다 — 정하지 않은 것은 결정 모음 한 곳으로
        if not re.search(r'결정|정할', name):
            tags = [t for t in TAG.findall(b) if not VERDICT.match(t)]
            if tags:
                add('inline-tags', '경고' if len(tags) >= 3 else '제안', where, f'본문에 이름표가 {len(tags)}개 있습니다({", ".join(tags[:3])}).',
                    '문장에서 이름표를 빼고, 정하지 않은 값은 결정 모음(> [!decide]- 질문)으로 옮기세요. 관련 절은 [[#절 이름]]으로 잇습니다.')
        # 10. 쓰는 사람의 목소리
        for m in NARRATE.finditer(b):
            add('narrator', '제안', where, f'「{m.group(0).lstrip(".!? ").strip()[:36]}…」은 제삼자가 남의 기획을 소개하는 말투입니다.',
                '기획자가 직접 판단을 말하게 쓰세요. 예: 「지금 저희에게는 … 가 맞다고 판단했습니다.」')

    if total > LIMITS['body_chars']:
        add('body-long', '경고', '문서', f'본문이 {total}자입니다.', '한 문서 한 결정. 독자가 다른 내용을 별도 문서로 나누세요.')
    if marks_total > LIMITS['marks_total']:
        add('mark-total', '제안', '문서', f'강조가 문서 전체에 {marks_total}곳입니다.', f"{LIMITS['marks_total']}곳 안으로 줄이세요.")
    if not any(re.search(r'다음\s*행동|할\s*일', h) for h, _ in main):
        add('no-actions', '제안', '문서', '다음 행동 절이 없습니다.', '## 다음 행동 | … 에 담당·기한이 있는 할 일을 두세요.')
    if not re.search(r'\[!(unknown|question|caution|warning|decide)\]|확인\s*필요|미확인', body):
        add('no-unknowns', '제안', '문서', '모르는 것·위험을 드러낸 곳이 없습니다.', '> [!unknown] 이나 확인 필요 절로 가정과 위험을 적으세요.')
    appx_chars = sum(len(_plain(b)) for _, b in appx)
    if total and appx_chars > total * 0.25:
        add('appendix-long', '제안', '부록', f'부록이 본문의 {appx_chars * 100 // total}%입니다.', '부록은 출처와 변경 이력만 두세요.')
    for h, _ in sections:
        if h.split('|')[0].strip() in ('부록',):
            add('appendix-content', '경고', '부록', '본문이 아닌 문안·상세가 부록에 있습니다.', '다른 독자를 위한 내용은 별도 문서로 옮기세요.')

    if str(fm.get('template', '')) in ('schedule', 'catalog'):
        # 찾아보는 유형: 결론 띠지·절 분량·표 행 수 같은 읽기형 규칙은 맞지 않는다
        keep = {'inline-tags', 'narrator', 'meta-reader', 'frontmatter', 'head-missing'}
        issues = [i for i in issues if i['id'] in keep]
    score = max(0, 100 - 8 * sum(i['level'] == '경고' for i in issues) - 3 * sum(i['level'] == '제안' for i in issues))
    return {'score': score, 'body_chars': total, 'sections': len(main), 'issues': issues}
