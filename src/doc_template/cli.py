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
    a = p.parse_args(argv)
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
