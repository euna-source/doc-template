"""목록·필터형(catalog): 한 절 안의 '### 그룹' + '#### 항목' + '- 필드: 값' 목록을 필터 줄이 붙은 표로.

머리말
  catalog:
    section: 조건표                # 이 절의 항목을 표로 만든다
    columns: [갱신, 앱푸시, …]      # 표 열 순서(항목 제목·번호 열은 자동)
    marks: [앱푸시, 알림목록]        # 켬·끔·미정·해당 없음 → 아이콘
    more: [대표 이미지, …]          # '핵심 열만'에서 숨길 열
    fold: {field: 묶음, value: 히스토리}   # 이 값의 그룹은 처음에 접는다
    filters:
      - {name: 묶음, field: 묶음, options: [현행, 백로그, 히스토리]}
      - {name: 갱신, field: 갱신, options: [신규, 수정], default: any, any: 변경사항 전부}
      - {name: 날짜, field: 갱신, options: {09-16 반영: 2026-09-16}}
    glossary: 열 설명               # 열 머리 ? 버튼이 여는 절(레이어)
"""
import html
import re
from bs4 import BeautifulSoup, NavigableString

esc = html.escape
MARK = {'켬': 'on', '끔': 'off', '미정': 'tbd', '해당 없음': 'na'}
ICON = {
    'push': '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="2.5" width="12" height="19" rx="2.6" fill="none" stroke="currentColor" stroke-width="1.9"/><rect x="8.2" y="5.2" width="7.6" height="3.4" rx="1"/><circle cx="12" cy="18" r="1.1"/></svg>',
    'list': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a6 6 0 0 0-6 6v3.6L4.4 15.4c-.5.7 0 1.6.8 1.6h13.6c.8 0 1.3-.9.8-1.6L18 12.6V9a6 6 0 0 0-6-6z"/><path d="M9.5 19a2.5 2.5 0 0 0 5 0z"/></svg>',
}
MARK_WORD = {'on': '뜸', 'off': '안 뜸', 'tbd': '미정', 'na': '해당 없음'}


def _slug(s):
    return re.sub(r'[^0-9A-Za-z가-힣]+', '-', s).strip('-').lower() or 'x'


def _opts(f):
    o = f.get('options') or []
    if isinstance(o, dict):
        return [(str(k), str(v)) for k, v in o.items()]
    return [(str(x), str(x)) for x in o]


def _field_items(ul):
    """'- 이름: 값' 목록 → [(이름, 값 HTML, 값 글자)]"""
    out = []
    for li in ul.find_all('li', recursive=False):
        first = next((c for c in li.children if not (isinstance(c, NavigableString) and not c.strip())), None)
        # 첫 글자 노드에서 '이름:'을 뗀다(markdown-it은 '- 이름: 값'을 <li>이름: 값</li>로 만든다)
        text_nodes = [c for c in li.descendants if isinstance(c, NavigableString)]
        if not text_nodes:
            continue
        t0 = text_nodes[0]
        m = re.match(r'\s*([^:：]{1,20})[:：]\s?', str(t0))
        if not m:
            continue
        name = m.group(1).strip()
        t0.replace_with(str(t0)[m.end():])
        if len(li.find_all('p', recursive=False)) == 1:
            li.find('p', recursive=False).unwrap()
        for bq in li.find_all('blockquote'):
            bq.name = 'div'; bq['class'] = ['msg']
            for p in bq.find_all('p'):
                p.unwrap()
        out.append((name, li.decode_contents().strip(), li.get_text(' ', strip=True)))
    return out


def _cell(name, html_, text, cfg):
    if name in cfg['marks']:
        k = MARK.get(text.strip(), '')
        ic = ICON['push' if '푸시' in name else 'list']
        return f'<span class="ic {k}" title="{esc(name)}: {esc(MARK_WORD.get(k, text))}">{ic}<span class="sr">{esc(MARK_WORD.get(k, text))}</span></span>'
    if name == cfg.get('update_field', '갱신'):
        parts = [p.strip() for p in text.split('·')]
        if parts and parts[0] in ('신규', '수정'):
            cls = 'new' if parts[0] == '신규' else 'mod'
            rest = ''.join(f'<span class="upd-sub">{esc(p)}</span>' for p in parts[1:] if p)
            return f'<span class="upd {cls}">{esc(parts[0])}</span>{rest}'
        return f'<span class="dim">{html_}</span>'
    if name == cfg.get('status_field', '상태'):
        kind = 'ok' if text.startswith('확정') else 'hold' if text.startswith(('백로그', '보류')) else 'tbd'
        return f'<span class="st {kind}"><i aria-hidden="true"></i><span>{html_}</span></span>'
    return html_


def build(soup, fm, section_name):
    """catalog 절의 h3·h4·ul을 표로 바꾼다. 반환: (필터 줄 HTML, 건수) — 필터 줄은 절 맨 앞에 넣는다."""
    cfg = dict(fm.get('catalog') or {})
    cfg['marks'] = [str(x) for x in (cfg.get('marks') or [])]
    cols = [str(x) for x in (cfg.get('columns') or [])]
    more = {str(x) for x in (cfg.get('more') or [])}
    fold = cfg.get('fold') or {}
    filters = cfg.get('filters') or []
    h2 = next((h for h in soup.find_all('h2') if h.get_text().split('|')[0].strip() == section_name), None)
    if h2 is None:
        return 0
    nodes, node = [], h2.find_next_sibling()
    while node is not None and node.name != 'h2':
        nodes.append(node); node = node.find_next_sibling()
    first = next((x for x in nodes if x.name in ('h3', 'h4')), None)
    if first is None:
        return 0
    slot = soup.new_tag('div')   # 표가 들어갈 자리
    first.insert_before(slot)
    body_rows, groups, total = [], [], 0
    gi, g_id, g_fold = 0, '', False
    head_cells = ''.join(f'<th scope="col" class="c-{_slug(c)}{" more" if c in more else ""}">{esc(c)}'
                         f'{"<button type=button class=qh data-gloss aria-label=" + chr(34) + esc(c) + " 설명" + chr(34) + ">?</button>" if cfg.get("glossary") else ""}</th>' for c in cols)
    i = nodes.index(first)
    pending_group = None
    while i < len(nodes):
        n = nodes[i]
        if n.name == 'h3':
            gi += 1
            g_id = f'g{gi}'
            note = ''
            j = i + 1
            while j < len(nodes) and nodes[j].name not in ('h3', 'h4'):
                note += str(nodes[j]); nodes[j].decompose(); j += 1
            pending_group = dict(id=g_id, title=n.decode_contents(), note=note, rows=[], vals=set())
            groups.append(pending_group)
            n.decompose(); i = j
            continue
        if n.name == 'h4':
            ul = n.find_next_sibling()
            items = _field_items(ul) if ul is not None and ul.name == 'ul' else []
            title = n.get_text(' ', strip=True)
            m = re.match(r'(#?\S+)\s+(.*)', title)
            num, name = (m.group(1), m.group(2)) if m and m.group(1).startswith('#') else ('', title)
            f = {k: (h, t) for k, h, t in items}
            data = ''.join(f' data-f-{_slug(k)}="{esc(t)}"' for k, h, t in items)
            upd = f.get(cfg.get('update_field', '갱신'), ('', ''))[1]
            ucls = ' u-new' if upd.startswith('신규') else ' u-mod' if upd.startswith('수정') else ''
            fold_val = f.get(fold.get('field', ''), ('', ''))[1] if fold else ''
            rid = f'r-{num.lstrip("#")}' if num else f'r-{_slug(name)}'
            typ = f.get('타입', ('', ''))[0]
            cells = ''.join(f'<td class="c-{_slug(c)}{" more" if c in more else ""}" data-label="{esc(c)}">{_cell(c, *f.get(c, ("", "")), cfg) if c in f else ""}</td>' for c in cols)
            row = (f'<tr class="row{ucls}" id="{rid}" data-g="{g_id}"{data}>'
                   f'<th scope="row" class="c-num">{esc(num)}</th><td class="c-name"><b class="ttl">{esc(name)}</b>{f"<span class=typ>{typ}</span>" if typ else ""}</td>{cells}</tr>')
            if pending_group is not None:
                pending_group['rows'].append(row)
                if fold_val:
                    pending_group['vals'].add(fold_val)
            else:
                body_rows.append(row)
            total += 1
            n.decompose()
            if ul is not None and ul.name == 'ul':
                ul.decompose()
            i += 2 if items else 1
            continue
        i += 1
    ncol = len(cols) + 2
    tbody = ''.join(body_rows)
    chips = []
    for g in groups:
        folded = bool(fold) and g['vals'] == {str(fold.get('value'))}
        chips.append(f'<a class="gchip" href="#{g["id"]}" data-g="{g["id"]}">{BeautifulSoup(g["title"], "html.parser").get_text()}</a>')
        tbody += (f'<tr class="grp{" folded" if folded else ""}" id="{g["id"]}" data-fold="{int(folded)}"><td colspan="{ncol}"><div class="gttl">'
                  f'<button type="button" class="gtog" aria-expanded="{str(not folded).lower()}" aria-controls="{g["id"]}">{g["title"]}</button>'
                  f'<span class="gcount" data-total="{len(g["rows"])}">{len(g["rows"])}행</span></div>'                  + (f'<div class="gnote">{g["note"]}</div>' if g['note'] else '') + '</td></tr>') + ''.join(g['rows'])
    # 필터 줄
    fbar = []
    for k, flt in enumerate(filters):
        opts = _opts(flt)
        default = str(flt.get('default', 'all'))
        default = next((pat for label, pat in opts if default in (label, pat)), default)   # 이름으로 적어도 값으로 맞춘다
        btns = [f'<button type="button" data-v="all" aria-pressed="{str(default == "all").lower()}">전체</button>']
        if flt.get('any'):
            btns.append(f'<button type="button" data-v="any" aria-pressed="{str(default == "any").lower()}">{esc(str(flt["any"]))}</button>')
        for label, pat in opts:
            btns.append(f'<button type="button" data-v="{esc(pat)}" aria-pressed="{str(pat == default).lower()}">{esc(label)}<span class="n"></span></button>')
        fbar.append(f'<div class="fgroup" role="group" aria-label="{esc(str(flt.get("name", "")))}" data-field="{_slug(str(flt.get("field", "")))}" data-default="{esc(default)}">'
                    f'<span class="flabel">{esc(str(flt.get("name", "")))}</span>{"".join(btns)}</div>')
    tools = ('<div class="ftools"><button type="button" id="cat-ftoggle" aria-expanded="false">필터</button><label class="fsearch"><span class="sr">검색</span><input type="search" id="cat-q" placeholder="문구·타입·조건 검색"></label>'
             f'{"<button type=button id=cat-more aria-pressed=false>핵심 열만</button>" if more else ""}'
             '<button type="button" id="cat-reset">필터 초기화</button><span class="fcount" id="cat-count" aria-live="polite"></span></div>')
    bar = (f'<div class="catbar" id="catbar"><div class="catbar-in"><div class="filters">{"".join(fbar)}</div>{tools}'
           f'<nav class="gchips" aria-label="그룹으로 이동">{"".join(chips)}</nav></div></div>')
    # 열 묶음 머리줄: column_groups: ['식별 3', '앱 푸시 1', …] — 번호·제목 열을 포함한 열 수
    all_cols = ['#', '_name'] + cols
    grow, k = '', 0
    for spec in (cfg.get('column_groups') or []):
        name_, _, cnt = str(spec).rpartition(' ')
        try:
            cnt = int(cnt)
        except ValueError:
            continue
        span_cols = all_cols[k:k + cnt]; k += cnt
        core = sum(1 for c in span_cols if c not in more)
        grow += f'<th scope="colgroup" colspan="{cnt}" data-span="{cnt}" data-span-core="{core}"{" class=more" if core == 0 else ""}>{esc(name_)}</th>'
    table = (f'<div class="cat-wrap" tabindex="0" role="region" aria-label="{esc(section_name)} 표"><table class="cat">'
             f'<thead>{f"<tr class=hg>{grow}</tr>" if grow else ""}<tr class="hc"><th scope="col" class="c-num">#</th><th scope="col" class="c-name">{esc(str(cfg.get("title_column", "항목")))}</th>{head_cells}</tr></thead>'
             f'<tbody>{tbody}</tbody></table></div>')
    slot.replace_with(BeautifulSoup(bar + table, 'html.parser'))
    return total
