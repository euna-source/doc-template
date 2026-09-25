"""여러 유형이 머리말로 켜 쓰는 부품: 국면 카드, 고정 2주 달력, 머리 버튼, 레이어(서랍), 탭,
일정표형 두 열(운영 흐름·부스팅), 변경 비교 표시.

머리말 예
  phases:   ['개시 전 | 9/22 ~ 10/6 | 9/22 ~ 10/6 | 2026-09-22 ~ 2026-10-06', …]   이름 | 카드 기간 | 달력 위 기간 | 시작 ~ 끝
  calendar: {from, to, round: 'A ~ B', key: [날짜…], deploy: 날짜, marks: {날짜: '말 / 둘째 줄'}, legend: {round, next, key, deploy}}
  buttons:  {버튼 이름: 절 이름}      layers: [절 이름…]      tabs: [절 이름…]
"""
import datetime as dt
import difflib
import html
import re
from bs4 import BeautifulSoup

esc = html.escape
WD = '월화수목금토일'
DATE_RE = re.compile(r'^\s*(\d{1,2})/(\d{1,2})')


def _date(v):
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v).strip())


def _range(v):
    a, _, b = str(v).partition('~')
    return _date(a), _date(b or a)


def parse_phases(fm):
    out = []
    for i, raw in enumerate(fm.get('phases') or [], 1):
        parts = [p.strip() for p in str(raw).split('|')]
        parts += [''] * (4 - len(parts))
        name, long_, short, span = parts[:4]
        try:
            a, b = _range(span) if span else (None, None)
        except ValueError:
            a = b = None
        out.append(dict(no=f'{i:02d}', id=f'p{i}', name=name, long=long_, short=short or long_, start=a, end=b))
    return out


def phases_html(phases):
    if not phases:
        return ''
    cards = ''.join(
        f'<a class="phase-card" href="#{p["id"]}" data-start="{p["start"] or ""}" data-end="{p["end"] or ""}">'
        f'<span class="pc-no">{p["no"]}</span><b>{esc(p["name"])}</b><span class="pc-when">{esc(p["long"])}</span>'
        f'<span class="pc-now" hidden>지금</span></a>' for p in phases)
    return f'<nav class="phase-cards" aria-label="국면">{cards}</nav>'


def calendar_html(fm, phases, anchors):
    """anchors: {date: element id} — 흐름에서 그 날짜에 해당하는 첫 줄. 날짜 칸은 그 날짜 이하의 가장 가까운 줄로 간다."""
    cal = fm.get('calendar') or {}
    if not cal.get('from'):
        return ''
    start, end = _date(cal['from']), _date(cal.get('to') or cal['from'])
    r0, r1 = _range(cal['round']) if cal.get('round') else (None, None)
    keys = {_date(k) for k in (cal.get('key') or [])}
    deploy = _date(cal['deploy']) if cal.get('deploy') else None
    marks = {_date(k): str(v) for k, v in (cal.get('marks') or {}).items()}
    ndays = (end - start).days + 1
    segs = []
    for p in phases:   # 달력 기간과 겹치는 만큼만, 날짜 칸과 같은 열에 걸친다
        if not p['start']:
            continue
        a, b = max(p['start'], start), min(p['end'], end)
        if a > b:
            continue
        c0, span = (a - start).days + 1, (b - a).days + 1
        segs.append(f'<a class="pn" href="#{p["id"]}" style="grid-column:{c0} / span {span}" data-start="{p["start"]}" data-end="{p["end"]}" '
                    f'title="{esc(p["name"])} · {esc(p["short"])}"><span>{p["no"]}</span><b>{esc(p["name"])}</b></a>')
    pn = ''.join(segs)
    days, d = [], start
    known = sorted(anchors)
    while d <= end:
        cls = ['day']
        if r0 and r0 <= d <= r1:
            cls.append('in')
        elif r1 and d > r1:
            cls.append('next')
        if d in keys:
            cls.append('key')
        if d == deploy:
            cls.append('deploy')
        if d.weekday() >= 5:
            cls.append('weekend')
        prior = [a for a in known if a <= d]
        href = f' href="#{anchors[prior[-1]]}"' if prior else ''
        label = '<br>'.join(esc(x.strip()) for x in marks.get(d, '').split(' / ') if x.strip())
        days.append(f'<a class="{" ".join(cls)}"{href} data-date="{d}"><span class="wd">{WD[d.weekday()]}</span>'
                    f'<span class="dn">{d.day}</span><span class="lb">{label}</span></a>')
        d += dt.timedelta(days=1)
    lg = cal.get('legend') or {}
    legend = ''.join(f'<span class="lg {k}"><i aria-hidden="true"></i>{esc(str(v))}</span>' for k, v in lg.items() if v)
    legend += '<span class="lg today"><i aria-hidden="true"></i>오늘</span>'
    for note in (cal.get('notes') or []):   # 조작 안내 문장(원문 보존용)
        legend += f'<span class="lg-note">{esc(str(note))}</span>'
    if cal.get('mobile_hint'):
        legend += f'<span class="cal-hint">{esc(str(cal["mobile_hint"]))}</span>'
    return (f'<div class="calband" id="calband"><div class="calband-in">'
            f'<div class="calgrid" style="--ndays:{ndays}">'
            f'{f"<nav class=pnav aria-label=국면으로 이동>{pn}</nav>" if pn else ""}'
            f'<nav class="cal" aria-label="날짜로 이동">{"".join(days)}</nav></div></div></div>'
            f'<p class="cal-legend">{legend}</p>')


def buttons_html(fm, names, layer_ids):
    items = []
    for label, target in (fm.get('buttons') or {}).items():
        sid = names.get(str(target).strip())
        if not sid:
            continue
        if sid in layer_ids:
            items.append(f'<button type="button" class="btn-sec" data-layer="{sid}" aria-haspopup="dialog">{esc(str(label))}</button>')
        else:
            items.append(f'<a class="btn-sec" href="#{sid}">{esc(str(label))}</a>')
    return f'<nav class="btn-row" aria-label="바로 가기">{"".join(items)}</nav>' if items else ''


# ── 일정표형: 국면 안의 '#### 이름' + 표 두 개를 두 열(시간표·카드)로 ─────────────
def _cells(tr):
    return [td.decode_contents().strip() for td in tr.find_all(['td', 'th'])]


def _heads(tb):
    th = tb.find('thead')
    return [c.get_text(strip=True) for c in th.find_all('th')] if th else []


def _timeline(tb, soup, used, year):
    rows = []
    for tr in tb.find('tbody').find_all('tr'):
        c = _cells(tr) + [''] * 4
        when, what, body, chips = c[:4]
        key = what.startswith('★')
        what = what.lstrip('★').strip()
        date_part, _, time_part = BeautifulSoup(when, 'html.parser').get_text().partition(' · ')
        rid = ''
        m = DATE_RE.match(date_part)
        if m and year:
            try:
                d = dt.date(year, int(m.group(1)), int(m.group(2)))
                if d not in used:
                    used[d] = f'd{d:%m%d}'
                    rid = used[d]
            except ValueError:
                pass
        chip_html = ''.join(
            f'<span class="chip {"op" if BeautifulSoup(x, "html.parser").get_text().strip().startswith("운영:") else "see"}">{x.strip()}</span>'
            for x in chips.split(' / ') if x.strip())
        rows.append(f'<div class="tl-row{" key" if key else ""}"{f" id={rid}" if rid else ""}>'
                    f'<div class="tl-when">{esc(date_part.strip())}{f"<small>{esc(time_part.strip())}</small>" if time_part else ""}</div>'
                    f'<div class="tl-what"><h5>{what}{"<span class=sr> (중요)</span>" if key else ""}</h5>{f"<p>{body}</p>" if body else ""}'
                    f'{f"<div class=chips>{chip_html}</div>" if chip_html else ""}</div></div>')
    return f'<div class="timeline">{"".join(rows)}</div>'


SIG = {'핵심': 'core', '노랑': 'warn', '빨강': 'red'}


def _cards(tb):
    out = []
    for tr in tb.find('tbody').find_all('tr'):
        c = _cells(tr) + [''] * 5
        sig, title, body, when, who = c[:5]
        kind, _, label = BeautifulSoup(sig, 'html.parser').get_text().partition(':')
        cls = SIG.get(kind.strip(), '')
        tag = ''
        if cls == 'core':
            tag = '<span class="sig core">핵심</span>'
        elif cls and label.strip():
            tag = f'<span class="sig {cls}">{esc(label.strip())}</span>'
        out.append(f'<div class="card{" " + cls if cls else ""}"><div class="card-main">{tag}<p class="ct">{title}</p>'
                   f'{f"<p class=cb>{body}</p>" if body else ""}</div>'
                   f'<div class="card-side">{f"<b>{when}</b>" if when else ""}{who}</div></div>')
    return f'<div class="cards">{"".join(out)}</div>'


def schedule_flow(soup, year):
    """h3(국면) 뒤의 h4+표 쌍을 두 열로. h3 '01 개시 전 | 기간'은 번호·이름·기간으로 나눈다. 반환: {날짜: id}."""
    used = {}
    n = 0
    for h3 in soup.find_all('h3'):
        m = re.match(r'\s*(\d{2})\s+(.+?)\s*\|\s*(.+)$', h3.get_text())
        if not m:
            continue
        n += 1
        pairs, node = [], h3.find_next_sibling()
        while node is not None and node.name not in ('h2', 'h3'):
            nxt = node.find_next_sibling()
            if node.name == 'h4':
                tb = node.find_next_sibling()
                if tb is not None and tb.name == 'table':
                    heads = _heads(tb)
                    kind = 'timeline' if heads[:1] == ['때'] else 'cards' if heads[:1] == ['신호'] else ''
                    if kind:
                        pairs.append((node, tb, kind))
                        nxt = tb.find_next_sibling()
            node = nxt
        head = BeautifulSoup(f'<div class="phase-h" id="p{n}"><span class="ph-no">{m.group(1)}</span><h3>{esc(m.group(2))}</h3>'
                             f'<span class="ph-when">{esc(m.group(3))}</span></div>', 'html.parser')
        h3.replace_with(head)
        if not pairs:
            continue
        cols = soup.new_tag('div', attrs={'class': 'cols'})
        pairs[0][0].insert_before(cols)
        for h4, tb, kind in pairs:
            inner = _timeline(tb, soup, used, year) if kind == 'timeline' else _cards(tb)
            col = BeautifulSoup(f'<div class="col col-{kind}"><h4>{h4.decode_contents()}</h4>{inner}</div>', 'html.parser')
            cols.append(col)
            h4.decompose(); tb.decompose()
    return used


# ── 탭: 지정한 절 안의 h3들을 탭으로 ───────────────────────────────
def tabs(section_nodes, soup, sid):
    heads = [x for x in section_nodes if getattr(x, 'name', None) == 'h3']
    if len(heads) < 2:
        return section_nodes
    first = section_nodes.index(heads[0])
    groups, cur = [], None
    for node in section_nodes[first:]:
        if getattr(node, 'name', None) == 'h3':
            cur = [node, []]
            groups.append(cur)
        elif cur is not None:
            cur[1].append(node)
    btns = ''.join(f'<button type="button" role="tab" id="{sid}-t{i}" aria-controls="{sid}-p{i}" aria-selected="{str(i == 0).lower()}"'
                   f'{"" if i == 0 else " tabindex=-1"}>{g[0].decode_contents()}</button>' for i, g in enumerate(groups))
    panels = ''.join(f'<div role="tabpanel" id="{sid}-p{i}" aria-labelledby="{sid}-t{i}"{"" if i == 0 else " hidden"}>'
                     f'{"".join(str(x) for x in g[1])}</div>' for i, g in enumerate(groups))
    box = BeautifulSoup(f'<div class="tabs"><div class="tablist" role="tablist">{btns}</div>{panels}</div>', 'html.parser')
    return section_nodes[:first] + [box]


# ── 변경 비교: '이전 「A」 → 이후 「B」' 줄에 지운 말·더한 말 표시 ──────────────
PAIR_SPLIT = '」 → 이후 「'


def _tok(s):
    return re.findall(r'\s+|[^\s·,.()「」]+|[·,.()「」]', s)


def _diff(a, b):
    ta, tb = _tok(a), _tok(b)
    ops = difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes()
    # 같음 구간이 공백·기호뿐이거나 낱말 하나면 변경으로 흡수해 구절 단위로 묶는다
    merged = []
    for op in ops:
        tag, i1, i2, j1, j2 = op
        if merged and tag == 'equal' and merged[-1][0] != 'equal':
            seg = ta[i1:i2]
            words = [t for t in seg if t.strip() and t not in '·,.()「」']
            if len(words) <= 1 and op is not ops[-1]:
                merged.append(('join', i1, i2, j1, j2)); continue
        merged.append(op)
    was, now, bw, bn = [], [], [], []
    def flush():
        x, y = ''.join(bw), ''.join(bn)
        if x.strip():
            was.append(f'<del>{esc(x.strip())}</del>' + (' ' if x.endswith(' ') else ''))
        if y.strip():
            now.append(f'<ins>{esc(y.strip())}</ins>' + (' ' if y.endswith(' ') else ''))
        bw.clear(); bn.clear()
    for tag, i1, i2, j1, j2 in merged:
        if tag == 'equal':
            flush()
            was.append(esc(''.join(ta[i1:i2]))); now.append(esc(''.join(tb[j1:j2])))
        else:
            bw.append(''.join(ta[i1:i2])); bn.append(''.join(tb[j1:j2]))
    flush()
    return ''.join(was), ''.join(now)


def _split_pair(txt):
    """'…이전 「A」 → 이후 「B」꼬리' → (앞, A, B, 꼬리). 「」가 겹쳐도 가운데 구분자와 마지막 」로 가른다."""
    if PAIR_SPLIT not in txt or '이전 「' not in txt:
        return None
    head, _, rest = txt.partition('이전 「')
    a, _, rest = rest.partition(PAIR_SPLIT)
    cut = rest.rfind('」')
    if cut < 0:
        return None
    return head, a, rest[:cut], rest[cut + 1:]


def history_diffs(soup):
    for li in soup.find_all('li'):
        parts = _split_pair(li.get_text())
        if not parts:
            continue
        head, a, b, tail = parts
        strong = li.find('strong')
        where = strong.get_text() if strong else head.strip().rstrip(':').strip()
        none = a.strip() in ('없음 · 신규', '없음')
        was, now = (esc(a), _diff('', b)[1]) if none else _diff(a, b)
        li.clear()
        li['class'] = ['chg']
        li.append(BeautifulSoup(
            f'{f"<b class=chg-where>{esc(where)}</b>" if where else ""}<div class="diff"><span class="k">이전</span>'
            f'<p class="was{" none" if none else ""}">{was}</p><span class="k">이후</span><p class="now">{now}</p></div>'
            f'{f"<p class=chg-tail>{esc(tail.strip())}</p>" if tail.strip() else ""}', 'html.parser'))
