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

mcp = _Server('doc-template', instructions='기획·리서치 문서를 옵시디언 Markdown으로 쓰고 HTML로 렌더한다. get_starter로 문법을 받고, list_themes로 색을 고른 뒤 render_document를 부른다. publish_document는 외부 공개라 사용자 확인 뒤에만 부른다.')
OUT = Path(os.environ.get('DOC_TEMPLATE_OUT', Path.home() / 'Documents' / 'doc-template'))

@mcp.tool()
def list_themes() -> list:
    """쓸 수 있는 테마와 대표 색. id를 render_document의 theme에 넣는다. 'mono'는 흑백, 'one:#HEX' 또는 'one:t3'는 한 가지 색 모드."""
    return all_themes()

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

def main():
    import sys
    transport = 'streamable-http' if '--http' in sys.argv else 'stdio'
    mcp.run(transport)

if __name__ == '__main__':
    main()
