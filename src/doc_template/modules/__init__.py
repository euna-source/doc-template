"""문서 템플릿 부품(모듈) — 부품 하나는 폴더 하나(module.json·style.css·script.js)다.

부품은 두 곳에 쓴다.
- 엔진 원고: 펜스 블록(예: ```verdict)을 렌더가 부품 마크업으로 바꾸고, 쓴 부품의 CSS만 페이지에 넣는다.
- 아무 HTML(kit): 이미 있는 페이지에 부품을 덧붙인다. 원본 구조는 건드리지 않고, 붙인 자리는 표식 주석으로 감싸서
  다시 붙이면 바꿔 끼우고(같은 결과), 떼면 원본과 바이트까지 같아진다. 「원본 사용성 먼저, 덧대기만」 원칙의 도구다.
"""
import html as _html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_START = '<!--doc-template-kit:start {id}-->'
_END = '<!--doc-template-kit:end {id}-->'
_BLOCK = re.compile(r'<!--doc-template-kit:start ([a-z0-9-]+)-->.*?<!--doc-template-kit:end \1-->', re.S)
_OPAQUE = re.compile(r'<script\b.*?</script\s*>|<style\b.*?</style\s*>|<!--.*?-->|<textarea\b.*?</textarea\s*>', re.S | re.I)


def read(path):
    """줄끝(CRLF)까지 그대로 읽는다 — 떼면 바이트까지 같게."""
    return Path(path).read_bytes().decode('utf-8')


def write(path, text):
    Path(path).write_bytes(text.encode('utf-8'))


def _tag_pos(page, rx, last=False):
    """스크립트·스타일·주석 안의 글자는 건너뛰고 진짜 태그 자리만 찾는다."""
    masked = _OPAQUE.sub(lambda m: ' ' * len(m.group(0)), page)
    hits = list(re.finditer(rx, masked, re.I))
    if not hits:
        return None
    return hits[-1] if last else hits[0]
GENERATOR = '<meta name="generator" content="doc-template kit">'


def catalog():
    """[{id, name, what, scope, data(넣을 자료 모양 예시)}] — 부품 목록."""
    out = []
    for d in sorted(p for p in ROOT.iterdir() if (p / 'module.json').is_file()):
        m = json.loads((d / 'module.json').read_text(encoding='utf-8'))
        m['files'] = [f.name for f in d.iterdir() if f.suffix in ('.css', '.js')]
        out.append(m)
    return out


def _mod(mid):
    d = ROOT / mid
    if not re.fullmatch(r'[a-z0-9-]+', mid or '') or not (d / 'module.json').is_file():
        raise ValueError(f'없는 부품입니다: {mid} (있는 것: {", ".join(m["id"] for m in catalog())})')
    css = (d / 'style.css').read_text(encoding='utf-8') if (d / 'style.css').exists() else ''
    js = (d / 'script.js').read_text(encoding='utf-8') if (d / 'script.js').exists() else ''
    return json.loads((d / 'module.json').read_text(encoding='utf-8')), css, js


def css(mid):
    return _mod(mid)[1]


def _json_script(mid, data):
    # </script> 같은 글자가 자료에 있어도 태그가 닫히지 않게
    s = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return f'<script type="application/json" data-dk-data="{mid}">{s}</script>'


def remove(page, ids=None):
    """붙인 부품을 뗀다(ids를 비우면 전부). 생성기 표식도 kit이 넣은 것이면 뗀다."""
    gen = _START.format(id='generator') + GENERATOR + _END.format(id='generator')
    want = None if ids is None else set(ids) | {i + '-body' for i in ids}
    page = _BLOCK.sub(lambda m: m.group(0) if m.group(1) == 'generator' or (want is not None and m.group(1) not in want) else '', page)
    if not [m for m in _BLOCK.finditer(page) if m.group(1) != 'generator']:
        page = page.replace(gen, '')
    return page


def apply(page, ids, data=None):
    """아무 HTML에 부품을 붙인다. ids 순서대로, 이미 붙은 같은 부품은 바꿔 끼운다. data는 {부품 id: 자료}."""
    data = data or {}
    if not ids:
        raise ValueError('붙일 부품을 하나 이상 고르세요')
    if not _tag_pos(page, r'</head\s*>') or not _tag_pos(page, r'</body\s*>'):
        raise ValueError('<head>와 <body>가 있는 HTML 문서에만 붙입니다')
    page = remove(page, set(ids))
    for mid in ids:
        meta, c, j = _mod(mid)
        if 'any' not in meta.get('scope', []):
            raise ValueError(f'{mid}는 엔진 원고 전용 부품입니다')
        if meta.get('data') is not None and mid not in data:
            raise ValueError(f'{mid} 부품에는 자료가 필요합니다(모양: {json.dumps(meta["data"], ensure_ascii=False)[:160]})')
        head = f'<style data-dk="{mid}">{c}</style>' if c else ''
        tail = (_json_script(mid, data[mid]) if mid in data else '') + (f'<script data-dk="{mid}">{j}</script>' if j else '')
        if head:
            i = _tag_pos(page, r'</head\s*>').start()
            page = page[:i] + _START.format(id=mid) + head + _END.format(id=mid) + page[i:]
        if tail:
            i = _tag_pos(page, r'</body\s*>', last=True).start()
            page = page[:i] + _START.format(id=mid + '-body') + tail + _END.format(id=mid + '-body') + page[i:]
    if 'name="generator" content="doc-template' not in page[:4000]:   # 배포(publish)가 kit 페이지를 알아보게
        h = _tag_pos(page, r'<head\b[^>]*>')
        if h:
            page = page[:h.end()] + _START.format(id='generator') + GENERATOR + _END.format(id='generator') + page[h.end():]
    return page


# ── 엔진 원고 블록: ```verdict ───────────────────────────────
_V = {'확정': 'v-ok', '추정': 'v-mid', '대략': 'v-mid', '불가': 'v-no', '못 셈': 'v-no'}
_VT = {'v-ok': '확정', 'v-mid': '추정', 'v-no': '불가'}


def verdict_html(text):
    """줄마다 「확정|추정|불가 | 무엇 | 조건」 → 세 칸 판정 상자. 칸 이름은 줄의 첫 값을 그대로 쓴다."""
    groups, names = {'v-ok': [], 'v-mid': [], 'v-no': []}, {}
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 2 or parts[0] not in _V:
            continue
        k = _V[parts[0]]; names.setdefault(k, parts[0])
        groups[k].append((parts[1], parts[2] if len(parts) > 2 else ''))
    e = _html.escape
    cols = ''.join(f'<section class="{k}"><h4>{e(names.get(k, _VT[k]))}</h4><ul>'
                   + ''.join(f'<li>{e(a)}{f"<small>{e(b)}</small>" if b else ""}</li>' for a, b in rows) + '</ul></section>'
                   for k, rows in groups.items() if rows)
    return f'<div class="dk-verdict">{cols}</div>'
