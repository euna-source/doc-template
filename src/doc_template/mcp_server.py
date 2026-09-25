"""doc-template MCP 서버(stdio). Claude Code·Claude Desktop·Codex에서 같은 도구를 쓴다."""
import os, re, datetime
from pathlib import Path
try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
from .render import render
from .themes_list import all_themes, describe
from .themes import ROOT
from .lint import review

mcp = _Server('doc-template', instructions='기획·리서치 문서를 옵시디언 Markdown으로 쓰고 HTML로 렌더한다. 순서: get_guide로 구조 원칙을 읽고 → get_starter로 뼈대를 받아 쓰고 → review_document로 구조를 점검해 경고를 고친 뒤 → list_themes에서 색을 골라 render_document. 원칙 요지: 결론을 띠지 한 문장으로 맨 위에, 소제목은 절의 결론 문장, 한 문서 한 독자(개발 상세·참가자 문안은 별도 문서), 절 600자·본문 3,000자 안, 표 8행 안, 강조는 문서 전체 1~3곳, 모르는 것은 따로, 다음 행동은 동사·담당·기한. publish_document는 외부 공개라 사용자 확인 뒤에만 부른다.')
OUT = Path(os.environ.get('DOC_TEMPLATE_OUT', Path.home() / 'Documents' / 'doc-template'))

@mcp.tool()
def list_themes() -> list:
    """쓸 수 있는 테마와 대표 색. id를 render_document의 theme에 넣는다. 'mono'는 흑백, 'one:#HEX' 또는 'one:t3'는 한 가지 색 모드."""
    return all_themes()

@mcp.tool()
def get_guide() -> str:
    """읽히는 문서의 구조 원칙(결론 먼저·소제목은 결론 문장·한 문서 한 독자·형식은 내용에 맞게·강조 절제·모르는 것 따로·다음 행동은 동사·담당·기한). 문서를 쓰기 전에 읽는다."""
    return (ROOT / 'guide.md').read_text(encoding='utf-8')

@mcp.tool()
def review_document(markdown: str) -> dict:
    """쓴 Markdown의 구조를 가이드 원칙대로 점검한다. score(100점)와 issues[{level 경고|제안, where, message, fix}]를 돌려준다. 경고를 고친 뒤 render_document를 부른다."""
    return review(markdown)

@mcp.tool()
def get_starter(kind: str = 'plan') -> str:
    """시작 문서(Markdown)와 문법. kind: plan(기획) | research(리서치). 머리말의 theme 한 줄로 색을 고른다."""
    if kind not in ('plan', 'research'):
        raise ValueError("kind는 plan 또는 research")
    return (ROOT / 'starters' / f'{kind}.md').read_text(encoding='utf-8')

@mcp.tool()
def render_document(markdown: str, theme: str = '', output_path: str = '', canonical_url: str = '', overwrite: bool = False) -> dict:
    """옵시디언 Markdown을 문서 템플릿 HTML(한 파일)로 만든다. theme을 비우면 머리말의 theme(없으면 t1).
    output_path를 비우면 ~/Documents/doc-template/<제목>-<날짜>.html 에 저장한다. 결과에 파일 경로와 대비 검사 결과가 있다."""
    html, rep = render(markdown, theme=theme or None, canonical=canonical_url or None)
    if not output_path:
        m = re.search(r'^short:\s*(.+)$', markdown, re.M) or re.search(r'^title:\s*(.+)$', markdown, re.M)
        name = re.sub(r'[\\/:*?"<>|\s]+', '-', (m.group(1) if m else 'document').strip())[:40] or 'document'
        OUT.mkdir(parents=True, exist_ok=True)
        output_path = str(OUT / f'{name}-{datetime.date.today():%y%m%d}.html')
    out = _safe_out(output_path, overwrite)
    out.write_text(html, encoding='utf-8')
    return {'path': str(out), **rep}

@mcp.tool()
def render_file(path: str, theme: str = '', overwrite: bool = False) -> dict:
    """Markdown(.md) 파일을 읽어 같은 폴더에 같은 이름의 .html로 렌더한다. 같은 이름의 HTML이 있으면 overwrite=True일 때만 덮어쓴다."""
    src = Path(path).expanduser().resolve()
    if src.suffix.lower() not in ('.md', '.markdown') or not src.is_file():
        raise ValueError('Markdown(.md) 파일만 렌더합니다')
    html, rep = render(src.read_text(encoding='utf-8'), theme=theme or None)
    out = _safe_out(str(src.with_suffix('.html')), overwrite)
    out.write_text(html, encoding='utf-8')
    return {'path': str(out), **rep}

@mcp.tool()
def publish_document(html_path: str, slug: str) -> dict:
    """렌더한 HTML을 GitHub Pages 저장소(환경변수 DOC_TEMPLATE_PAGES_REPO)에 올리고 공개 URL을 돌려준다. 외부 공개이므로 사용자 확인 뒤에만 부른다."""
    from .publish import publish
    return publish(html_path, slug)

def _safe_out(path, overwrite):
    out = Path(path).expanduser().resolve()
    if out.suffix.lower() != '.html':
        raise ValueError('출력 파일은 .html 이어야 합니다')
    if out.exists() and not overwrite:
        raise FileExistsError(f'이미 있는 파일입니다: {out} (덮어쓰려면 overwrite=True)')
    out.parent.mkdir(parents=True, exist_ok=True)
    return out

@mcp.prompt()
def plan_document(topic: str, audience: str = '대표·개발·디자인') -> str:
    """기획 문서 초안을 가이드 원칙대로 쓰게 하는 프롬프트."""
    return (f'주제: {topic}\n읽는 사람: {audience}\n'
            'doc-template의 get_guide로 원칙을 읽고, get_starter(kind=plan) 뼈대에 맞춰 옵시디언 Markdown으로 기획 문서를 써 줘. '
            '결론을 띠지 한 문장으로 먼저 쓰고, 각 절 소제목은 그 절의 결론 문장으로. 이 독자가 결정할 내용만 남기고 다른 독자용 상세는 별도 문서로 뺀다. '
            'review_document로 점검해 경고를 모두 고친 다음 render_document로 HTML을 만들어 경로를 알려 줘.')

def main():
    import sys
    transport = 'streamable-http' if '--http' in sys.argv else 'stdio'
    mcp.run(transport)

if __name__ == '__main__':
    main()
