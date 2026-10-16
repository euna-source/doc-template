import argparse, json, sys
from pathlib import Path
from . import __version__
from .render import render
from .themes_list import all_themes
from .themes import ROOT

def main(argv=None):
    p = argparse.ArgumentParser(prog='doc-template', description='옵시디언 Markdown → 기획·리서치 문서 HTML')
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('render', help='Markdown을 HTML로'); r.add_argument('src'); r.add_argument('-o', '--out'); r.add_argument('--theme'); r.add_argument('--canonical')
    sub.add_parser('themes', help='테마 목록과 대표 색')
    rv = sub.add_parser('review', help='문서 구조 점검(가이드 원칙)'); rv.add_argument('src')
    sub.add_parser('guide', help='읽히는 문서의 구조 원칙 출력')
    s = sub.add_parser('starter', help='시작 문서 출력'); s.add_argument('kind', choices=['plan', 'research', 'schedule', 'catalog']); s.add_argument('-o', '--out')
    pb = sub.add_parser('publish', help='GitHub Pages에 올리기'); pb.add_argument('html'); pb.add_argument('slug'); pb.add_argument('--repo')
    sub.add_parser('mcp', help='MCP 서버(stdio) 실행')
    kt = sub.add_parser('kit', help='부품(모듈): 목록 · 아무 HTML에 붙이기 · 떼기')
    kts = kt.add_subparsers(dest='ktcmd', required=True)
    kts.add_parser('list', help='부품 목록과 넣을 자료 모양')
    ka = kts.add_parser('apply', help='HTML에 부품 붙이기(원본 구조는 그대로, 다시 붙이면 바꿔 끼움)'); ka.add_argument('html'); ka.add_argument('-o', '--out'); ka.add_argument('--with', dest='mods', required=True, help='쉼표로: look,toggle,history,sources'); ka.add_argument('--data', action='append', default=[], help='부품=자료.json (history·sources)')
    kr2 = kts.add_parser('remove', help='붙인 부품 떼기(전부 떼면 원본과 같음)'); kr2.add_argument('html'); kr2.add_argument('-o', '--out'); kr2.add_argument('--only', help='쉼표로 일부만')
    k = sub.add_parser('kinds', help='문서 템플릿 모음 유형 렌더(prd·research·catalog·schedule·minutes·pt)')
    ks = k.add_subparsers(dest='kcmd', required=True)
    kr = ks.add_parser('render', help='원고를 유형 디자인으로'); kr.add_argument('kind'); kr.add_argument('src'); kr.add_argument('-o', '--out'); kr.add_argument('--theme'); kr.add_argument('--font')
    ks.add_parser('call', help='표준 입력 JSON {fn, args, kwargs} → 표준 출력 JSON {result} (스튜디오·모음 페이지 연결용)')
    a = p.parse_args(argv)
    if a.cmd == 'kit':
        from . import modules as _M
        if a.ktcmd == 'list':
            print(json.dumps(_M.catalog(), ensure_ascii=False, indent=1)); return
        src = Path(a.html); page = _M.read(src)
        if a.ktcmd == 'apply':
            data = {}
            for kv in a.data:
                k_, _, f_ = kv.partition('=')
                data[k_.strip()] = json.loads(Path(f_).read_text(encoding='utf-8'))
            out_html = _M.apply(page, [m.strip() for m in a.mods.split(',') if m.strip()], data)
        else:
            out_html = _M.remove(page, [m.strip() for m in a.only.split(',')] if a.only else None)
        out = Path(a.out or src); _M.write(out, out_html)
        print(json.dumps({'out': str(out.resolve()), 'bytes': len(out_html.encode())}, ensure_ascii=False)); return
    if a.cmd == 'kinds':
        from .kinds import call as _kcall
        if a.kcmd == 'render':
            from .kinds.render import render as _krender
            h = _krender(Path(a.src).read_text(encoding='utf-8'), a.kind, theme=a.theme, font=a.font)
            out = Path(a.out or Path(a.src).with_suffix('.html')); out.write_text(h, encoding='utf-8')
            print(json.dumps({'out': str(out.resolve()), 'kind': a.kind}, ensure_ascii=False))
        else:
            try:
                req = json.loads(sys.stdin.buffer.read().decode('utf-8'))
                if not (isinstance(req, dict) and isinstance(req.get('fn'), str) and isinstance(req.get('args', []), list) and isinstance(req.get('kwargs', {}), dict)):
                    raise ValueError('요청은 {"fn": 이름, "args": [...], "kwargs": {...}} 모양이어야 한다')
                res = {'result': _kcall(req['fn'], *req.get('args', []), **req.get('kwargs', {}))}
            except (ValueError, TypeError, KeyError) as exc:  # JSON 오류(ValueError 하위)도 여기 — 부른 쪽이 같은 종류로 다시 올린다
                res = {'error': {'type': 'ValueError' if isinstance(exc, ValueError) else type(exc).__name__, 'message': str(exc)}}
            sys.stdout.buffer.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
        return
    if a.cmd == 'render':
        html, rep = render(Path(a.src).read_text(encoding='utf-8'), theme=a.theme, canonical=a.canonical)
        out = Path(a.out or Path(a.src).with_suffix('.html')); out.write_text(html, encoding='utf-8')
        print(json.dumps({'out': str(out.resolve()), **rep}, ensure_ascii=False))
    elif a.cmd == 'review':
        from .lint import review
        r = review(Path(a.src).read_text(encoding='utf-8'))
        print(f"구조 점수 {r['score']} · 본문 {r['body_chars']}자 · 절 {r['sections']}개")
        for i in r['issues']:
            print(f"  [{i['level']}] {i['where']} — {i['message']} → {i['fix']}")
    elif a.cmd == 'guide':
        sys.stdout.write((ROOT / 'guide.md').read_text(encoding='utf-8'))
    elif a.cmd == 'themes':
        for t in all_themes():
            print(f"{t['id']:8} {t['name']}  (최저 대비 {t['contrast_min']})")
        print('one:<#HEX|t1~t6>  한 가지 색 모드. 예: one:#1957B8, one:t3')
    elif a.cmd == 'starter':
        text = (ROOT / 'starters' / f'{a.kind}.md').read_text(encoding='utf-8')
        (Path(a.out).write_text(text, encoding='utf-8') if a.out else sys.stdout.write(text))
    elif a.cmd == 'publish':
        from .publish import publish
        print(json.dumps(publish(a.html, a.slug, a.repo), ensure_ascii=False))
    elif a.cmd == 'mcp':
        from .mcp_server import main as m; m()

if __name__ == '__main__':
    main()
