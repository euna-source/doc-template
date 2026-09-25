"""MCP 서버를 stdio로 띄워 도구 목록·테마·렌더를 실제 호출한다."""
import asyncio, json, sys, tempfile, os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command=sys.executable, args=['-m', 'doc_template.mcp_server'], env={**os.environ, 'DOC_TEMPLATE_OUT': tempfile.mkdtemp()})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = [t.name for t in (await s.list_tools()).tools]
            th = await s.call_tool('list_themes', {})
            st = await s.call_tool('get_starter', {'kind': 'plan'})
            md = st.content[0].text
            g = await s.call_tool('get_guide', {})
            rv = await s.call_tool('review_document', {'markdown': md})
            prompts = [p.name for p in (await s.list_prompts()).prompts]
            rd = await s.call_tool('render_document', {'markdown': md, 'theme': 'mono'})
            res = json.loads(rd.content[0].text)
            print(json.dumps({'tools': tools, 'themes': len(json.loads(th.content[0].text)) if th.content and th.content[0].text.startswith('[') else len(th.content),
                              'render': {k: res[k] for k in ('theme', 'sections', 'contrast_min', 'structure_score')}, 'prompts': prompts, 'guide_chars': len(g.content[0].text), 'review': json.loads(rv.content[0].text)['score'], 'exists': os.path.exists(res['path'])}, ensure_ascii=False))
asyncio.run(main())
