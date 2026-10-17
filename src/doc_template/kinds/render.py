#!/usr/bin/env python3
"""템플릿별 문서 렌더러 — Markdown 한 벌을 템플릿(plan·research·catalog·schedule·minutes·pt)의 디자인으로 그린다.

빈 템플릿 미리보기, 작성 중 초안, 탈고본이 모두 이 한 곳을 지난다(같은 모양 보장).
Markdown 규칙
  # 제목              · 제목 바로 아래 `- 키: 값` 줄은 머리 메타(상위·상태·버전·일시·참석 …)
  > 문장              · 첫 인용은 결론 띠지, 이후 인용은 알림 상자
  ## 이름 — 질문       · 절(번호 자동). 「 — 」 뒤는 이 절이 답하는 질문
  ### 소제목 · 표 · - 목록 · 1. 목록 · - [ ] / - [x] 체크 · ![설명](주소) 그림
  _기울임_            · 자리표시 안내(빈 템플릿에서 회색 안내문)
  ## 출처             · 맨 아래 접힌 출처 띠로 간다
"""
import html, re, sys
from . import themes as _themes

e = lambda s: html.escape(str(s), quote=True)


def inline(s):
    s = e(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]', r'<span class="ts">[\1]</span>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])_(.+?)_(?!\w)', r'<span class="hint">\1</span>', s)
    s = re.sub(r'!\[([^\]]*)\]\(((?:https?://|files/)[^)\s]+)\)', r'<img alt="\1" src="\2">', s)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2">\1</a>', s)
    return s


OPEN_L = ('미결', '확인 필요', '발언 충돌', '보류')
DEC_L = ('결정', '합의')


def _li(t):
    ck = re.match(r'\[( |x|X)\]\s*(.*)', t)
    if ck: return f'<li class="ck{" on" if ck.group(1) != " " else ""}">{inline(ck.group(2))}</li>'
    lab = re.match(r'(결정|미결|할 일|합의|확인 필요)\s*[:：]\s*(.*)', t)   # 「결정: …」
    if lab:
        k = 'open' if lab.group(1) in OPEN_L else 'dec' if lab.group(1) in DEC_L else 'todo'
        return f'<li class="k-{k}"><b>{e(lab.group(1))}</b> {inline(lab.group(2))}</li>'
    bl = re.match(r'\*\*([^*]{1,20})\*\*', t)                             # 「**결정**: …」 머리말
    k = ''
    if bl:
        w = bl.group(1)
        k = ' class="lb-dec"' if w in DEC_L else ' class="lb-open"' if w in OPEN_L else ''
    return f'<li{k}>{inline(t)}</li>'


def _nest(items, i=0):
    """(들여쓰기, 번호?, li) 목록 → 중첩 ul/ol. 더 깊은 줄은 바로 위 항목 안으로 들어간다."""
    def walk(i):
        base, tag, parts = items[i][0], 'ol' if items[i][1] else 'ul', []
        while i < len(items) and items[i][0] >= base:
            if items[i][0] == base:
                li = items[i][2]; i += 1
                if i < len(items) and items[i][0] > base:
                    sub, i = walk(i); li = li[:-5] + sub + '</li>'
                parts.append(li)
            else:
                sub, i = walk(i); parts.append('<li>' + sub + '</li>')
        return f'<{tag}>' + ''.join(parts) + f'</{tag}>', i
    return walk(i)[0] if items else ''


def split_front(md):
    fm = {}
    if md.startswith('---\n'):
        end = md.find('\n---', 4)
        if end > 0:
            for ln in md[4:end].splitlines():
                if ':' in ln:
                    k, v = ln.split(':', 1); fm[k.strip()] = v.strip()
            md = md[end + 4:].lstrip('\n')
    return fm, md


def parse(md):
    """→ dict(title, meta[(k,v)], lede, sections[{name, q, blocks[html]}], sources[html])"""
    fm, md = split_front(md)
    doc = {'fm': fm, 'title': fm.get('title', ''), 'meta': [], 'lede': '', 'pre': [], 'sections': [], 'sources': []}
    lines = md.splitlines()
    i, cur = 0, None
    def out(h):
        (cur['blocks'] if cur is not None else doc['pre']).append(h)
    while i < len(lines):
        ln = lines[i]; s = ln.strip()
        if not s: i += 1; continue
        if s.startswith('# ') and not doc['title']:
            doc['title'] = s[2:].strip(); i += 1
            while i < len(lines) and re.match(r'\s*-\s+[^:\[]{1,12}:', lines[i]):
                k, v = re.sub(r'^\s*-\s+', '', lines[i]).split(':', 1); doc['meta'].append((k.strip(), v.strip())); i += 1
            continue
        if s.startswith('# '):
            doc['title'] = doc['title'] or s[2:]; i += 1; continue
        if s.startswith('## '):
            name = s[3:].strip()
            name, _, q = name.partition(' — ') if ' — ' in name else name.partition(' | ')
            name = re.sub(r'^\d+\s+', '', name.strip())
            cur = {'name': name, 'q': q.strip(), 'blocks': []}
            (doc['sources'] if name in ('출처', '참고', '원자료') else doc['sections']).append(cur)
            if name in ('출처', '참고', '원자료'): cur = cur  # 출처 절 블록도 cur에 쌓인다
            i += 1; continue
        if s.startswith('### '):
            out(f'<h3>{inline(s[4:])}</h3>'); i += 1; continue
        if s.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i])); i += 1
            txt = ' '.join(b for b in buf if not b.startswith('[!'))
            kind = re.match(r'\[!(\w+)\]', buf[0] or '')
            if not doc['lede'] and cur is None and not kind:
                doc['lede'] = inline(txt)
            else:
                out(f'<div class="call {e(kind.group(1)) if kind else ""}">{inline(txt)}</div>')
            continue
        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                r = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{2,}:?', c) for c in r if c): rows.append(r)
                i += 1
            if rows:
                head = ''.join(f'<th scope="col">{inline(c)}</th>' for c in rows[0])
                body = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in rows[1:])
                out(f'<div class="tw dk-table dk-frame"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        m = re.match(r'(\s*)([-*]|\d+\.)\s+(.*)', ln)
        if m:
            items = []   # (들여쓰기, 번호목록?, li html)
            while i < len(lines):
                mm = re.match(r'(\s*)([-*]|\d+\.)\s+(.*)', lines[i])
                if not mm: break
                items.append((len(mm.group(1).replace('\t', '  ')), mm.group(2)[0].isdigit(), _li(mm.group(3))))
                i += 1
            out(_nest(items)); continue
        if s.startswith('!['):
            out(f'<figure>{inline(s)}</figure>'); i += 1; continue
        if s in ('---', '***'):
            out('<hr>'); i += 1; continue
        buf = [ln]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'\s*([#>|]|[-*]\s|\d+\.\s|!\[)', lines[i]):
            buf.append(lines[i]); i += 1
        parts = [inline(line.rstrip()) + (' <br class="prose-break">' if line.endswith('  ') and n < len(buf)-1 else ' ') for n, line in enumerate(buf)]
        out('<p>' + ''.join(parts).strip() + '</p>')
    return doc


CSS = '''
:root{--bg:#fff;--sunken:#F7F7F8;--desk:#F2F2F4;--fg:#121212;--fg2:#3F3F46;--fg3:#6B6B73;--line:#EAEAED;--line2:#DEDEE2;--brand:#07ED21;--brand-ink:#067D14;--brand-soft:#DCFCE0;--mod-ink:#A63F08;--mod-soft:#FFE8D6;color-scheme:light}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.7 "Pretendard Variable",Pretendard,-apple-system,BlinkMacSystemFont,system-ui,sans-serif;word-break:keep-all;overflow-wrap:break-word;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:underline;text-decoration-color:var(--line2);text-underline-offset:3px}
.hint{color:#9A9AA3;font-style:normal;background:repeating-linear-gradient(90deg,transparent 0 3px,transparent 3px 6px)}
code{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--sunken);padding:1px 5px;border-radius:4px}
.page{max-width:1080px;margin:0 auto;padding:48px 32px 0}
.eyebrow{margin:0 0 8px;font-size:13px;font-weight:600;color:var(--fg3)}
h1{margin:0 0 10px;font-size:30px;line-height:1.3;letter-spacing:-.02em}
.meta{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;margin:0;font-size:13px;color:var(--fg3)}
.meta b{color:var(--fg);font-weight:600}.meta .st{padding:1px 9px;border-radius:999px;background:var(--brand-soft);color:var(--brand-ink);font-weight:700}
.btns{display:flex;gap:6px;margin:14px 0 0}.btn{display:inline-flex;align-items:center;height:32px;padding:0 14px;border-radius:8px;background:var(--fg);color:#fff;font-size:13px;font-weight:700;text-decoration:none}.btn.o{background:#fff;color:var(--fg);box-shadow:inset 0 0 0 1px var(--line2)}
.lede{margin:24px 0 0;padding:16px 20px;border-radius:12px;background:var(--brand-soft);font-size:16px;line-height:1.6}.lede::before{content:"결론";margin-right:10px;font-weight:800;color:var(--brand-ink)}
.sec{padding:32px 0;border-top:1px solid var(--line)}.sec:first-child{border-top:0}
.sh{display:grid;grid-template-columns:44px minmax(0,1fr);gap:0 8px;align-items:baseline}
.sn{color:var(--brand-ink);font-weight:700;font-size:14px}.sh h2{margin:0;font-size:22px;letter-spacing:-.01em}.sq{grid-column:2;margin:2px 0 0;font-size:14px;color:var(--fg3)}
.sb{margin-left:52px;margin-top:14px}.sb>*+*{margin-top:12px}.sb p{margin:0}.sb p+p{margin-top:.75em}
h3{margin:18px 0 6px;font-size:16px}
ul,ol{margin:0;padding-left:20px}li+li{margin-top:4px}
li.ck{list-style:none;margin-left:-20px}li.ck::before{content:"☐";margin-right:8px;color:var(--fg3)}li.ck.on::before{content:"☑";color:var(--brand-ink)}
li[class^="k-"]{list-style:none;margin-left:-20px}li[class^="k-"] b{display:inline-block;min-width:44px;margin-right:6px;font-size:12.5px}
li.k-dec b{color:var(--brand-ink)}li.k-open b{color:var(--mod-ink)}li.k-todo b{color:var(--fg)}
.ts{color:#9A9AA3;font-size:.9em;font-variant-numeric:tabular-nums}
li.lb-dec>strong:first-child{color:var(--brand-ink)}li.lb-open>strong:first-child{color:var(--mod-ink)}
li.lb-dec::marker{color:var(--brand)}li.lb-open::marker{color:#FF7A1A}
ul ul,ol ul{margin-top:4px;list-style:circle}
.tw{overflow-x:auto;border:1px solid var(--line2);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}th{background:var(--sunken);font-size:13px;color:var(--fg2);white-space:nowrap}
figure{margin:0}figure img{max-width:100%;border:1px solid var(--line2);border-radius:10px}
.call{padding:12px 16px;border-radius:10px;background:var(--sunken);font-size:14px}.call.decide,.call.unknown{background:var(--mod-soft)}
.tray{margin-top:48px;background:var(--desk);color:var(--fg3);font-size:13px}
.tray details{max-width:1080px;margin:0 auto;padding:14px 32px 28px}.t-plan .tray details,.t-minutes .tray details{max-width:1440px}.tray summary{cursor:pointer}.tray .tb{margin-top:10px}.tray .tb>*+*{margin-top:8px}
/* plan: 왼쪽 고정 목차 */
.t-plan .shell{display:grid;grid-template-columns:200px minmax(0,1fr);gap:40px;max-width:1240px;margin:0 auto;padding:48px 32px 0}
.t-plan .page{padding:0;max-width:none;margin:0;min-width:0}
.toc{position:sticky;top:32px;align-self:start;font-size:13px}.toc p{margin:0 0 12px;font-weight:700;display:flex;gap:8px;align-items:center}.toc p::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--brand)}
.toc ol{list-style:none;padding:0;display:grid;gap:10px}.toc a{text-decoration:none;color:var(--fg3)}.toc a b{font-weight:500;margin-right:10px}
.t-plan .head{padding-bottom:22px;border-bottom:2px solid var(--fg)}
/* research */
.t-research .sh{display:block}.t-research .sn{display:none}.t-research .sq{margin-top:4px}.t-research .sb{margin-left:0}
/* catalog */
.fbar{position:sticky;top:0;z-index:2;display:flex;gap:8px;align-items:center;padding:10px 0;background:#fff}.fbar input{flex:1;max-width:320px;height:34px;padding:0 12px;border:1px solid var(--line2);border-radius:8px;font:inherit;font-size:14px}.fbar span{font-size:13px;color:var(--fg3)}
.rules{border:1px solid var(--line2);border-radius:12px}.rules details+details{border-top:1px solid var(--line)}.rules summary{cursor:pointer;padding:10px 14px;font-size:14px}.rules summary b{margin-right:10px}.rules .rb{padding:0 14px 12px 14px;font-size:14px;color:var(--fg2)}
/* schedule */
.tabs{position:sticky;top:0;z-index:2;display:flex;gap:6px;overflow-x:auto;padding:12px 0;background:#fff;border-bottom:1px solid var(--line)}.tabs a{flex:none;padding:6px 14px;border-radius:999px;border:1px solid var(--line2);font-size:13px;text-decoration:none}.tabs a:first-child{background:var(--fg);color:#fff;border-color:var(--fg)}
/* minutes */
/* minutes: 왼쪽 목차 · 한눈에(2단) · 화자 · 안건 2단 기사 · 후속 업무·다음 일정·미결 */
.t-minutes .shell{display:grid;grid-template-columns:200px minmax(0,1fr);gap:40px;max-width:1440px;margin:0 auto;padding:40px 32px 0}
.t-minutes .page{padding:0;max-width:none;margin:0;min-width:0}.t-minutes h1{font-size:28px}
.t-minutes .head{padding-bottom:20px;border-bottom:2px solid var(--fg)}
.t-minutes .toc .ttl{margin:0 0 6px;font-size:12.5px;color:var(--fg2);font-weight:700}.t-minutes .toc .ttl::before{display:none}
.blk{padding:22px 0 10px}.blk>h2{margin:0 0 12px;font-size:17px}
.blk.glance ul{columns:2;column-gap:36px}.blk.glance li{break-inside:avoid;margin:0 0 8px}
.arts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 40px;margin-top:18px}
.art{border-top:2px solid var(--fg);padding:14px 0 26px}.art h2{margin:0 0 12px;font-size:17px;line-height:1.45}
.art ul{padding-left:18px}.art li{font-size:14px;line-height:1.7}.art .tw{margin:10px 0}
.t-minutes .blk.full{border-top:2px solid var(--fg);margin-top:10px}
/* pt */
.t-pt body,body.t-pt{background:var(--desk)}.slides{display:grid;gap:24px;max-width:960px;margin:0 auto;padding:32px}
.slide{aspect-ratio:16/9;background:#fff;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08);padding:48px 56px;display:flex;flex-direction:column;justify-content:center;gap:14px;overflow:hidden}
.slide h2{margin:0;font-size:30px}.slide.cover h1{font-size:40px}.slide .sq{margin:0}
@media (max-width:760px){.page,.t-plan .shell{padding:28px 16px 0}.t-plan .shell{grid-template-columns:1fr}.toc{display:none}.sb{margin-left:0}.sh{grid-template-columns:36px minmax(0,1fr)}
 .t-minutes .shell{grid-template-columns:1fr;padding:24px 16px 0}.arts{grid-template-columns:1fr}.blk.glance ul{columns:1}h1{font-size:24px}.tray details{padding-inline:16px}.slide{padding:24px}.slide h2{font-size:20px}}
'''

CSS += '''
/* 본문과 표의 폭은 해당 콘텐츠 열을 따른다. */
.page,.sb,.art,.blk,.slide,.tw,.fbar{min-width:0}
p,li,dd,blockquote{overflow-wrap:anywhere;line-break:strict}
p,blockquote{text-wrap:pretty}
h1,h2,h3{word-break:keep-all;overflow-wrap:anywhere;text-wrap:balance}
.fbar input{min-width:0}.fbar span{flex-shrink:0}
.tw table{min-width:480px}.tw{max-width:100%}
.slide{overflow:visible;aspect-ratio:auto;min-height:420px}
@media(max-width:760px){
 .slides{padding:20px 16px}.slide{min-height:0;padding:24px 20px}
 .slide.cover h1{font-size:28px}.slide .tw{width:100%}
}
@media(max-width:600px){br.prose-break{display:none}}
'''

LABEL = {'plan': '개발요건정의서', 'research': '리서치', 'catalog': '조건표', 'schedule': '운영 정책', 'minutes': '회의록', 'pt': '발표'}


def meta_html(doc):
    parts = []
    for k, v in doc['meta']:
        if k in ('상태',): parts.append(f'<span class="st">{inline(v)}</span>')
        elif k in ('버전',): parts.append(f'<b>버전 {inline(v)}</b>')
        elif k in ('원문', '링크'): continue
        else: parts.append(f'<span>{e(k)} {inline(v)}</span>')
    return '<p class="meta">' + ''.join(parts) + '</p>' if parts else ''


def section(s, n, tpl):
    q = f'<p class="sq">{inline(s["q"])}</p>' if s['q'] else ''
    body = ''.join(s['blocks'])
    if tpl == 'catalog' and s['name'].startswith('공통 규칙'):
        body = re.sub(r'<ul>(.*?)</ul>', lambda m: '<div class="rules">' + ''.join(
            (lambda t: f'<details><summary><b>{t[0]}</b>{t[1]}</summary><div class="rb">{t[1]}</div></details>')(
                (li.split(':', 1) + [''])[:2] if ':' in li else (li, ''))
            for li in re.findall(r'<li>(.*?)</li>', m.group(1))) + '</div>', body, count=1, flags=re.S)
    if tpl == 'catalog' and '<table>' in body:
        body = '<div class="fbar"><input type="search" placeholder="표에서 찾기" data-f><span data-n></span></div>' + body
    return f'<section class="sec" id="s{n}"><div class="sh"><span class="sn">{n:02d}</span><h2>{inline(s["name"])}</h2>{q}</div><div class="sb">{body}</div></section>'


DT_THEMES = ('paper', 't1', 't2', 't3', 't4', 't5', 't6', 'mono')


def _doc_template(md, theme):
    """리서치형은 doc-template 엔진 그대로(기준 시안이 이 엔진의 출력이다)."""
    from ..render import render as _engine_render
    if not md.startswith('---'): md = '---\ntemplate: research\n---\n' + md
    return _engine_render(md, theme=theme if theme in DT_THEMES else None)[0]


KINDS = ('prd', 'research', 'catalog', 'schedule', 'minutes', 'pt')


def render(md, tpl, standalone=True, note='', theme=None, font=None, transcript=None, canonical_url=None):
    """tpl: KINDS 중 하나(prd=기획서형 개발요건정의서). theme: themes.themes()의 id(c8·paper·t1~t6·mono), font: sans·serif-head·serif"""
    if tpl not in KINDS:
        raise ValueError(f'유형은 {" · ".join(KINDS)} 중 하나(기획서형은 prd — 엔진의 plan은 기획안 문서다)')
    tpl = 'plan' if tpl == 'prd' else tpl
    saved_theme = split_front(md)[0].get('theme', '').strip("\"'")
    theme = theme or saved_theme or 'mono'
    if tpl == 'research':
        h = _doc_template(md, 'mono' if theme == 'c8' else theme)
        extra = _themes.style('c8' if theme == 'c8' else False, font) + '<style>em{color:var(--muted);font-style:normal}</style>'
        h = h.replace('</head>', extra + '</head>', 1)
        return _themes.monochrome_html(h) if theme == 'mono' else h
    h = _render(md, tpl, standalone, note, theme, font)
    h = _themes.monochrome_html(h) if theme == 'mono' else h
    if tpl == 'minutes' and standalone:
        from .minutes_actions import attach
        h = attach(h, transcript=transcript, canonical_url=canonical_url)
    return h


def _render(md, tpl, standalone, note, theme, font):
    doc = parse(md)
    fm = doc['fm']
    eyebrow = fm.get('eyebrow') or f'크리에이터클럽 · {LABEL.get(tpl, "문서")}'
    link = dict(doc['meta']).get('원문') or dict(doc['meta']).get('링크')
    if link and not re.match(r'https?://', link): link = None   # javascript: 등 다른 스킴은 링크로 만들지 않는다
    title = inline(doc['title'] or '제목 없음')
    secs = ''.join(section(s, n, tpl) for n, s in enumerate(doc['sections'], 1))
    pre = ''.join(doc['pre'])
    src = ''.join(b for s in doc['sources'] for b in s['blocks'])
    nsrc = sum(len(re.findall(r'<li', b)) or 1 for s in doc['sources'] for b in s['blocks'])
    tray = f'<footer class="tray"><details><summary>출처 · {nsrc}</summary><div class="tb">{src}</div></details></footer>' if src else ''
    lede = f'<p class="lede">{doc["lede"]}</p>' if doc['lede'] else ''
    btns = '<p class="btns"><span class="btn">버전 기록</span>' + (f'<a class="btn o" href="{e(link)}">원문에서 보기</a>' if link else '') + '</p>'
    if tpl == 'plan':
        toc = ''.join(f'<li><a href="#s{n}"><b>{n:02d}</b>{inline(s["name"])}</a></li>' for n, s in enumerate(doc['sections'], 1))
        body = (f'<div class="shell"><nav class="toc"><p>{e(LABEL["plan"])}</p><ol>{toc}</ol></nav><main class="page">'
                f'<header class="head"><p class="eyebrow">{e(eyebrow)}</p><h1>{title}</h1>{meta_html(doc)}{btns}</header>{lede}{pre}{secs}</main></div>')
    elif tpl == 'minutes':
        btns = ''  # Shared copy toolbar is attached after rendering.
        FULL = ('한눈에', '참석·화자', '화자', '참석', '안건 지도', '후속 업무', '다음 일정', '미결·확인 필요', '미결', '확인 필요')
        def blk(sct, n):
            cls = 'blk glance' if sct['name'] == '한눈에' else 'blk full' if sct['name'] not in ('참석·화자', '화자', '참석', '안건 지도') else 'blk'
            return f'<section class="{cls}" id="s{n}"><h2>{inline(sct["name"])}</h2>{"".join(sct["blocks"])}</section>'
        def art(sct, n):
            h = inline(sct['name']) + (f' — {inline(sct["q"])}' if sct['q'] else '')
            return f'<article class="art" id="s{n}"><h2>{h}</h2>{"".join(sct["blocks"])}</article>'
        S = list(enumerate(doc['sections'], 1))
        head_b = [x for x in S if x[1]['name'] in FULL[:5] and x[1]['name'] not in FULL[5:]]
        tail_b = [x for x in S if x[1]['name'] in FULL[5:]]
        arts = [x for x in S if x[1]['name'] not in FULL]
        toc = ''.join(f'<li><a href="#s{n}">{inline(sc["name"])}{(" — " + inline(sc["q"])) if sc["q"] and sc["name"] not in FULL else ""}</a></li>' for n, sc in S)
        body = (f'<div class="shell"><nav class="toc"><p>회의록</p><p class="ttl">목차</p><ol>{toc}</ol></nav><main class="page">'
                f'<header class="head"><h1>{title}</h1>{meta_html(doc)}{btns}</header>{lede}{pre}'
                + ''.join(blk(sc, n) for n, sc in head_b)
                + f'<div class="arts">{"".join(art(sc, n) for n, sc in arts)}</div>'
                + ''.join(blk(sc, n) for n, sc in tail_b) + '</main></div>')
    elif tpl == 'pt':
        slides = f'<section class="slide cover"><p class="eyebrow">{e(eyebrow)}</p><h1>{title}</h1>{meta_html(doc)}</section>' + ''.join(
            f'<section class="slide" id="s{n}"><h2>{inline(s["name"])}</h2>{f"<p class=sq>{inline(s[chr(113)])}</p>" if s["q"] else ""}{"".join(s["blocks"])}</section>'
            for n, s in enumerate(doc['sections'], 1))
        body = f'<main class="slides">{slides}</main>'
    else:
        tabs = ''
        if tpl == 'schedule':
            tabs = '<nav class="tabs">' + ''.join(f'<a href="#s{n}">{inline(s["name"])}</a>' for n, s in enumerate(doc['sections'], 1)) + '</nav>'
        body = f'<main class="page"><header class="head"><p class="eyebrow">{e(eyebrow)}</p><h1>{title}</h1>{meta_html(doc)}{btns}</header>{lede}{pre}{tabs}{secs}</main>'
    body += tray
    js = '''<script>document.querySelectorAll('[data-f]').forEach(inp=>{const sec=inp.closest('.sb'),rows=[...sec.querySelectorAll('tbody tr')],n=sec.querySelector('[data-n]');const up=()=>{const q=inp.value.trim().toLowerCase();let c=0;rows.forEach(r=>{const ok=!q||r.textContent.toLowerCase().includes(q);r.hidden=!ok;c+=ok});n.textContent=c+'행'};inp.addEventListener('input',up);up()})</script>'''
    if not standalone:
        return body
    tcss = tjs = ''
    if 'dk-table' in body:   # 표 반응형 부품(선 끊김·잘림 없이, 좁으면 카드로)
        from .. import modules as _M
        _m, tcss, _j = _M._mod('table'); tjs = f'<script data-dk="table">{_j}</script>'
        tcss = '\n' + tcss
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(re.sub("<[^>]+>", "", title))}</title><meta name="robots" content="noindex">'
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'
            f'<style>{CSS}{tcss}</style>{_themes.style(theme, font)}</head><body class="t-{e(tpl)}">{note}{body}{js}{tjs}</body></html>')


if __name__ == '__main__':
    tpl, src = sys.argv[1], sys.argv[2]  # python -m doc_template.kinds.render <유형> <원고> [출력]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    h = render(open(src).read(), tpl)
    if out: open(out, 'w').write(h); print(out)
    else: sys.stdout.write(h)
