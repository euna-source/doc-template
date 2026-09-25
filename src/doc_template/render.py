"""옵시디언 Markdown → 문서 템플릿 HTML(한 파일).

머리말(front matter)
  template: plan | research          theme: t1~t6 · paper · mono · one:#HEX · one:t3
  kind, code, title, deck, status(draft|review|done), meta(이름: 값 목록), obi(label, text, cells[h,p])
본문 규칙
  ## 이름 | 소제목      절. '|' 왼쪽은 목차·절 번호 옆 이름, 오른쪽은 큰 제목(없으면 같은 말)
  ==구절==              노랑(강조 면) — 절마다 한 구절 권장
  > [!note|caution|unknown] 이름   알림 상자(참고·주의·미확인). ']-'는 접힘, ']+'는 펼친 채 접이
  > [!decide]- 질문     결정 모음 항목(접이). 표지 아래 '정하지 않은 것 N가지' 줄과 관련 절 표시가 자동으로 붙는다
  [[#절 이름]]          그 절로 가는 링크(옵시디언 제목 링크)
  > 문장 \n > — 출처      인용(마지막 줄이 '— '로 시작하면 출처)
  - [ ] / - [/] / - [x] 할 일 @담당 ~기한   다음 행동(대기·진행·완료)
  | 표 |                  모바일에서 카드. 첫 칸이 '★ '로 시작하면 추천 행
  {{가안}}              이름표(태그)
  ```stats  줄마다 "값 | 단위 | 설명"
  [^n] 와 '## 출처' 목록   각주 ↔ 출처. 출처 줄 끝의 {확인|일부|미확인}
  ## 변경 이력 표         이력 표
"""
import html, os, re
from pathlib import Path
import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from bs4 import BeautifulSoup
from .themes import resolve, css_vars, audit
from .lint import review

ROOT = Path(__file__).resolve().parent / 'assets'
TPL = ROOT
esc = html.escape

ICONS = {
    'note': '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.6v.2"/></svg>',
    'caution': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5 2.8 19.5h18.4z"/><path d="M12 10v4.2"/><path d="M12 17v.2"/></svg>',
    'unknown': '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.4"/><path d="M12 16.8v.2"/></svg>',
    'decide': '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>',
}
CALLOUT_ALIAS = {'note': 'note', 'info': 'note', 'tip': 'note', 'caution': 'caution', 'warning': 'caution',
                 'danger': 'caution', 'unknown': 'unknown', 'question': 'unknown', 'todo': 'unknown',
                 'decide': 'decide', 'decision': 'decide'}
CALLOUT_LABEL = {'note': '참고', 'caution': '주의', 'unknown': '미확인', 'decide': '정할 것'}
STATE = {'확인': 'full', '일부': 'half', '미확인': ''}
STATUS = {'draft': ('', '초안'), 'review': ('half', '검토 중'), 'done': ('full', '확정')}
CHECK_SVG = '<svg viewBox="0 0 12 12"><path d="m2.5 6.2 2.3 2.3 4.7-5"/></svg>'


def _md():
    return MarkdownIt('commonmark', {'html': False, 'typographer': False}).use(front_matter_plugin).enable('table').enable('strikethrough')


def _inline(text):
    """==강조==, {{이름표}}, [^n] 각주를 HTML로(마크다운 렌더 뒤 텍스트에 적용)."""
    text = re.sub(r'==(.+?)==', r'<mark>\1</mark>', text)
    text = re.sub(r'\{\{(.+?)\}\}', r'<span class="tag">\1</span>', text)
    text = re.sub(r'\[\^(\w+)\]', lambda m: f'<sup class="ref"><a href="#r{m.group(1)}" aria-label="출처 {m.group(1)}">{m.group(1)}</a></sup>', text)
    return text


# 한글 조사(CCO-121은)는 경계로 본다: 영문·숫자·밑줄·하이픈·슬래시만 이어진 글자로 친다
KEY = re.compile(r'(?<![A-Za-z0-9_/-])([A-Z][A-Z0-9]{1,9}-\d{1,6})(?![A-Za-z0-9_-])')
MDLINK = re.compile(r'\[([^\]]+)\]\((https?://(?:[^\s()]|\([^\s()]*\))+)\)')


def _linkify(text, fm):
    """머리·메타 값: [글](https://…)은 링크로, CCO-121 같은 티켓 번호는 머리말 jira(또는 DOC_TEMPLATE_JIRA) 주소로 잇는다."""
    base = str(fm.get('jira') or os.environ.get('DOC_TEMPLATE_JIRA') or '').rstrip('/')
    out, pos = [], 0
    for m in MDLINK.finditer(text):
        out.append(('t', text[pos:m.start()])); out.append(('a', m.group(1), m.group(2))); pos = m.end()
    out.append(('t', text[pos:]))
    html_out = []
    for part in out:
        if part[0] == 'a':
            html_out.append(f'<a href="{esc(part[2])}" target="_blank" rel="noopener">{esc(part[1])}</a>')
        elif base.startswith(('https://', 'http://')):
            html_out.append(KEY.sub(lambda k: f'<a href="{esc(base)}/browse/{k.group(1)}" target="_blank" rel="noopener">{k.group(1)}</a>', esc(part[1])))
        else:
            html_out.append(esc(part[1]))
    return ''.join(html_out)


def parse(md_text):
    md = _md()
    tokens = md.parse(md_text)
    fm = {}
    if tokens and tokens[0].type == 'front_matter':
        fm = yaml.safe_load(tokens[0].content) or {}
    body = md.render(md_text)
    return fm, body


def _sections(soup):
    """h2 단위로 <section>을 만든다. '이름 | 소제목' 규칙 적용. 출처·변경 이력은 부록으로."""
    out, sec = [], None
    for node in list(soup.contents):
        if getattr(node, 'name', None) == 'h2':
            raw = node.get_text()
            name, _, head = raw.partition('|')
            name, head = name.strip(), (head.strip() or name.strip())
            sec = {'name': name, 'head': head, 'nodes': [], 'appendix': name in ('출처', '부록', '변경 이력', '출처·이력')}
            out.append(sec)
        else:
            if sec is None:
                sec = {'name': '', 'head': '', 'nodes': [], 'appendix': False, 'intro': True}
                out.append(sec)
            sec['nodes'].append(node)
    return out


def _transform_blocks(soup, fm):
    decides = []
    # 알림 상자
    for bq in soup.find_all('blockquote'):
        first = bq.find('p')
        m = re.match(r'\s*\[!(\w+)\]([+-]?)[ \t]*(.*)', first.decode_contents(), re.S) if first else None
        if m:
            kind = CALLOUT_ALIAS.get(m.group(1).lower(), 'note')
            fold = m.group(2) or ('-' if kind == 'decide' else '')
            rest = m.group(3).split('\n', 1)
            title = rest[0].strip() or CALLOUT_LABEL[kind]
            remainder = rest[1] if len(rest) > 1 else ''
            first.clear()
            if remainder.strip():
                first.append(BeautifulSoup(remainder, 'html.parser'))
            else:
                first.decompose()
            if fold:
                # 접이 상자: 제목(summary)만 보이고 누르면 펼친다. 결정 항목은 번호를 붙인다
                attrs = {'class': f'callout {kind}'}
                if fold == '+':
                    attrs['open'] = ''
                new = soup.new_tag('details', attrs=attrs)
                num = ''
                if kind == 'decide':
                    decides.append(new)
                    new['id'] = f'd{len(decides)}'
                    num = f'<span class="dn">{len(decides):02d}</span>'
                    head = num + f'<span class="dq">{title}</span>'
                else:
                    head = ICONS[kind] + f'<span class="dq">{title}</span>'
                new.append(BeautifulSoup(f'<summary class="callout-label">{head}</summary>', 'html.parser'))
                body = soup.new_tag('div', attrs={'class': 'callout-body'})
                for ch in list(bq.contents):
                    body.append(ch)
                # '관련:' 줄은 배경 문단과 떼어 따로 둔다
                for para in body.find_all('p'):
                    head_, sep, rel = para.decode_contents().partition('\n관련:')
                    if sep:
                        para.clear(); para.append(BeautifulSoup(head_, 'html.parser'))
                        para.insert_after(BeautifulSoup(f'<p class="rel">관련:{rel}</p>', 'html.parser'))
                new.append(body)
            else:
                new = soup.new_tag('aside', attrs={'class': f'callout {kind}', 'aria-label': CALLOUT_LABEL[kind]})
                new.append(BeautifulSoup(f'<p class="callout-label">{ICONS[kind]}{esc(title)}</p>', 'html.parser'))
                for ch in list(bq.contents):
                    new.append(ch)
            bq.replace_with(new)
        else:
            ps = bq.find_all('p')
            cite = ''
            if ps:
                lines = ps[-1].decode_contents().split('\n')
                if lines[-1].strip().startswith(('—', '--')):
                    cite = lines[-1].strip().lstrip('—- ').strip()
                    rest = '\n'.join(lines[:-1]).strip()
                    if rest:
                        ps[-1].clear(); ps[-1].append(BeautifulSoup(rest, 'html.parser'))
                    else:
                        ps[-1].decompose()
            inner = '<br>'.join(p.decode_contents() for p in bq.find_all('p'))
            bq.replace_with(BeautifulSoup(f'<blockquote class="pull">{inner}{f"<cite>{cite}</cite>" if cite else ""}</blockquote>', 'html.parser'))
    # 표 → 카드 표, 추천 행
    for tb in soup.find_all('table'):
        for tr in tb.find_all('tr'):
            td = tr.find('td')
            if td and td.get_text().strip().startswith('★'):
                tr['class'] = ['pick']
                td.string = td.get_text().strip().lstrip('★').strip()
                td.append(BeautifulSoup(' <span class="tag">추천</span>', 'html.parser'))
        for th in tb.find_all(['th', 'td']):
            if th.get('style', '').startswith('text-align:right'):
                th['class'] = ['num']; del th['style']
        ncols = max((len(tr.find_all(['th', 'td'])) for tr in tb.find_all('tr')), default=0)
        compare = bool(tb.find(class_='num')) or ncols >= 5
        wrap = soup.new_tag('div', attrs={'class': 'table compare' if compare else 'table stack'})
        tb.wrap(wrap)
        if compare:
            hint = soup.new_tag('p', attrs={'class': 'table-hint'}); hint.string = '옆으로 밀어 보기 →'
            wrap.insert_after(hint)
    # 할 일 목록
    for ul in soup.find_all('ul'):
        lis = ul.find_all('li', recursive=False)
        if lis and all(re.match(r'\s*\[[ xX/]\]', li.get_text()) for li in lis):
            items = []
            for li in lis:
                txt = li.decode_contents().strip()
                if txt.startswith('<p>'):
                    txt = re.sub(r'^<p>|</p>$', '', txt)
                m = re.match(r'\[([ xX/])\]\s*(.*)', txt, re.S)
                state = {'x': 'done', 'X': 'done', '/': 'doing', ' ': ''}[m.group(1)]
                body = m.group(2)
                who = re.search(r'@(\S+)', body); due = re.search(r'~(\S+)', body)
                body = re.sub(r'\s*[@~]\S+', '', body).strip()
                sr = {'done': '완료: ', 'doing': '진행 중: ', '': ''}[state]
                items.append(f'<li class="{state}"><span class="box" aria-hidden="true">{CHECK_SVG if state == "done" else ""}</span>'
                             f'<span class="what">{f"<span class=sr>{sr}</span>" if sr else ""}{body}</span>'
                             f'<span class="who"><span>{esc(who.group(1)) if who else "담당 미정"}</span><span>{esc(due.group(1)) if due else "기한 미정"}</span></span></li>')
            ul.replace_with(BeautifulSoup(f'<ul class="actions">{"".join(items)}</ul>', 'html.parser'))
    # 수치 블록
    for code in soup.find_all('code', class_='language-stats'):
        rows = [l.split('|') for l in code.get_text().strip().splitlines() if l.strip()]
        cells = ''.join(f'<div><b>{esc(r[0].strip())}<small>{esc(r[1].strip()) if len(r) > 1 else ""}</small></b><span>{esc(r[2].strip()) if len(r) > 2 else ""}</span></div>' for r in rows)
        code.parent.replace_with(BeautifulSoup(f'<div class="stats">{cells}</div>', 'html.parser'))
    # 그림
    for img in soup.find_all('img'):
        p = img.parent
        cap = img.get('title', '')
        fig = f'<figure class="figure"><img src="{esc(img["src"])}" alt="{esc(img.get("alt", ""))}" decoding="async">{f"<figcaption>{esc(cap)}</figcaption>" if cap else ""}</figure>'
        (p if p.name == 'p' and len(p.contents) == 1 else img).replace_with(BeautifulSoup(fig, 'html.parser'))
    return decides


def _xrefs(soup, names):
    """[[#절 이름]] · [[#절 이름|보이는 말]] → 그 절 링크. 이름이 정확히 같은 절만 잇고, 못 찾으면 글자만 남긴다. 코드 안은 건드리지 않는다."""
    pat = re.compile(r'\[\[#([^\]|]+)(?:\|([^\]]+))?\]\]')
    for t in list(soup.find_all(string=pat)):
        if t.find_parent(['code', 'pre']):
            continue
        raw, out, pos = str(t), [], 0
        for m in pat.finditer(raw):
            key, label = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
            sid = names.get(key)
            out.append(esc(raw[pos:m.start()], quote=False))
            out.append(f'<a class="xref" href="#{sid}">{esc(label)}</a>' if sid else esc(label, quote=False))
            pos = m.end()
        out.append(esc(raw[pos:], quote=False))
        t.replace_with(BeautifulSoup(''.join(out), 'html.parser'))


def _keys(soup, fm):
    """본문의 티켓 번호(CCO-121 등)도 머리말 jira 주소가 있으면 링크로. 이미 링크·코드 안은 건드리지 않는다."""
    base = str(fm.get('jira') or os.environ.get('DOC_TEMPLATE_JIRA') or '').rstrip('/')
    if not base.startswith(('https://', 'http://')):
        return
    for t in list(soup.find_all(string=KEY)):
        if t.find_parent(['a', 'code', 'pre']):
            continue
        t.replace_with(BeautifulSoup(KEY.sub(lambda k: f'<a href="{esc(base)}/browse/{k.group(1)}" target="_blank" rel="noopener">{k.group(1)}</a>', esc(str(t), quote=False)), 'html.parser'))


def _sources(nodes, soup):
    """'## 출처' 목록을 출처 목록으로: - [제목](url) — 메타 {확인}"""
    html_out = []
    for n in nodes:
        if getattr(n, 'name', None) in ('ul', 'ol') and n.find('li'):
            lis = []
            for i, li in enumerate(n.find_all('li', recursive=False), 1):
                raw = li.decode_contents().strip()
                raw = re.sub(r'^<p>|</p>$', '', raw)
                st = re.search(r'\{(확인|일부|미확인)\}\s*$', raw)
                raw = re.sub(r'\s*\{(확인|일부|미확인)\}\s*$', '', raw)
                title, _, meta = raw.partition(' — ')
                dot = STATE.get(st.group(1) if st else '미확인', '')
                label = {'full': '원문 확인', 'half': '일부 확인', '': '미확인'}[dot]
                lis.append(f'<li id="r{i}"><span>{title}<span class="src-meta">{meta}</span></span><span class="state"><i class="dot {dot}" aria-hidden="true"></i>{label}</span></li>')
            html_out.append('<p class="legend"><span class="state"><i class="dot full" aria-hidden="true"></i>원문 확인</span><span class="state"><i class="dot half" aria-hidden="true"></i>일부 확인</span><span class="state"><i class="dot" aria-hidden="true"></i>미확인</span></p>')
            html_out.append(f'<ol class="sources">{"".join(lis)}</ol>')
        else:
            html_out.append(str(n))
    return ''.join(html_out)


def render(md_text, theme=None, template=None, canonical=None):
    fm, body = parse(md_text)
    theme_spec = str(theme or fm.get('theme') or 't1')
    th = resolve(theme_spec)
    soup = BeautifulSoup(_inline(body), 'html.parser')
    decides = _transform_blocks(soup, fm)
    secs = _sections(soup)
    # 절 id를 미리 매겨 [[#절]] 링크와 결정 항목 ↔ 관련 절을 잇는다
    names, k = {}, 0
    for s in secs:
        if not s.get('intro') and not s['appendix']:
            k += 1; s['sid'] = f's{k}'
            for key in (s['name'], s['head'], f"{s['name']} | {s['head']}"):
                names.setdefault(key, s['sid'])
    _xrefs(soup, names)
    _keys(soup, fm)
    pending, hub = {}, ''
    for d in decides:
        for a in d.find_all('a', class_='xref'):
            ids = pending.setdefault(a['href'][1:], [])
            if d['id'] not in ids:
                ids.append(d['id'])
    for s in secs:
        tags = [x for x in s['nodes'] if getattr(x, 'name', None)]
        if s.get('sid') and not hub and any(x is d or d in x.find_all('details') for x in tags for d in decides):
            hub = s['sid']
    main, appendix, toc = [], [], []
    n = 0
    for s in secs:
        inner = ''.join(str(x) for x in s['nodes'])
        if s.get('intro'):
            main.append(inner); continue
        if s['appendix']:
            appendix.append(f'<h2>{esc(s["head"])}</h2>' + (_sources(s['nodes'], soup) if s['name'].startswith('출처') else re.sub(r'class="table (stack|compare)"', 'class="table log"', inner)))
            continue
        n += 1
        sid = s['sid']
        toc.append(f'<li><a href="#{sid}"><span class="n">{n:02d}</span>{esc(s["name"])}</a></li>')
        ids = pending.get(sid, [])
        chip = (f'<a class="sec-pending" href="#{ids[0]}">정할 것 {len(ids)}</a>' if ids else '')
        main.append(f'<section id="{sid}" aria-labelledby="{sid}-t"><a class="sec-num" href="#{sid}"><b>{n:02d}</b>{esc(s["name"])}</a>{chip}'
                    f'<h2 id="{sid}-t">{_inline(esc(s["head"]))}</h2>{inner}</section>')
    if appendix:
        names_ap = [s['name'] for s in secs if s['appendix']]
        label = '·'.join(dict.fromkeys('출처' if n.startswith('출처') else n for n in names_ap)) or '출처·이력'
        toc.append(f'<li><a href="#refs"><span class="n">··</span>{esc(label)}</a></li>')
        main.append(f'<section class="appendix" id="refs" aria-labelledby="refs-t">{"".join(appendix)}</section>')
    toc_html = ''.join(toc)

    title = str(fm.get('title', '제목 없는 문서'))
    kind = str(fm.get('kind', '기획 문서'))
    short = str(fm.get('short', title.replace('\n', ' ')))
    dot, stext = STATUS.get(str(fm.get('status', 'draft')), STATUS['draft'])
    # 상태는 머리말에 status를 적었을 때만 보인다(없는 정보를 '초안'으로 채우지 않는다)
    meta = [('상태', f'<span class="state"><i class="dot {dot}" aria-hidden="true"></i>{stext}</span>')] if fm.get('status') else []
    for k, v in (fm.get('meta') or {}).items():
        meta.append((esc(str(k)), _linkify(str(v), fm)))
    meta_html = ''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in meta[:6])
    obi = fm.get('obi') or {}
    obi_html = ''
    if obi:
        cells = ''.join(f'<div><h2>{esc(str(c.get("h", "")))}</h2><p>{_inline(esc(str(c.get("p", ""))))}</p></div>' for c in (obi.get('cells') or [])[:3])
        obi_html = (f'<section class="obi" aria-labelledby="obi-title"><div class="obi-head"><span class="obi-label" id="obi-title">{esc(str(obi.get("label", "결론")))}</span>'
                    f'<p>{_inline(esc(str(obi.get("text", ""))))}</p></div>{f"<div class=obi-grid>{cells}</div>" if cells else ""}</section>')
    if decides:
        # 표지 아래 한 줄: 정하지 않은 것의 수와 결정 모음으로 가는 링크. 문구는 머리말 pending으로 바꾼다({n}이 수)
        line = str(fm.get('pending') or '아직 정하지 않은 것이 {n}가지 있습니다.').replace('{n}', str(len(decides)))
        obi_html += f'<p class="pending"><span>{esc(line)}</span><a href="#{hub}">모아 보기<span aria-hidden="true"> →</span></a></p>'

    tpl = (TPL / 'page.html').read_text()
    css = (TPL / 'doc.css').read_text().replace('/*@THEME*/', _theme_css(th)).replace(
        '/*@PRINT*/', ':root,:root:not([data-theme="light"]),:root[data-theme="dark"]{' + css_vars(th, 'light') + ';--bg:#FFFFFF;--body-size:11pt;color-scheme:light}')
    js = (TPL / 'doc.js').read_text()
    repl = {
        '@TITLE': esc(title.replace('\n', ' ')), '@SHORT': esc(short), '@KIND': esc(kind.split('·')[0].strip()),
        '@DESC': esc(str(fm.get('deck', ''))[:150]), '@CANONICAL': f'<link rel="canonical" href="{esc(canonical)}">' if canonical else '',
        '@ISSUE_L': esc(kind), '@ISSUE_R': _linkify(str(fm.get('code', '')), fm), '@EYEBROW': esc(str(fm.get('eyebrow', fm.get('topic', '')))),
        '@H1': '<br>'.join(esc(x) for x in title.split('\n')), '@DECK': esc(str(fm.get('deck', ''))), '@META': meta_html, '@OBI': obi_html,
        '@TOC': toc_html, '@NSEC': str(n), '@MAIN': ''.join(main), '@FOOT': esc(str(fm.get('footer', f'{kind} · 문서 템플릿'))),
        '@THEME_COLOR_L': th['light']['bg'], '@THEME_NAME': esc(th.get('meta', {}).get('name', theme_spec)),
        '/*@CSS*/': css, '/*@JS*/': js,
    }
    out = tpl
    for k, v in repl.items():
        out = out.replace(k, v)
    out = '\n'.join(line.rstrip() for line in out.split('\n'))
    if th.get('meta', {}).get('bw'):
        out = out.replace('<html lang="ko">', '<html lang="ko" data-bw>', 1)
    rv = review(md_text)
    return out, {'theme': theme_spec, 'sections': n, 'contrast_min': min(r[3] for r in audit(th)),
                 'contrast_fail': [r for r in audit(th) if r[3] < 4.5],
                 'structure_score': rv['score'], 'structure_issues': rv['issues'], 'decisions': len(decides)}


def _theme_css(th):
    l, d = css_vars(th, 'light'), css_vars(th, 'dark')
    return (f':root{{{l};color-scheme:light}}\n'
            f'@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{{d};color-scheme:dark}}}}\n'
            f':root[data-theme="dark"]{{{d};color-scheme:dark}}\n')
