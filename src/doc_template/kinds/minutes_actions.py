"""Shared minutes toolbar for studio and dedicated meeting-skill renderers."""
import html
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent


def attach(page, transcript=None, canonical_url=None):
    """Attach copy-only controls; transcript must be the unedited source text."""
    if 'id="meeting-copy-data"' in page:
        raise ValueError('minutes toolbar already attached')
    if '</header>' not in page or '</head>' not in page or '</body>' not in page:
        raise ValueError('complete HTML with header required')
    if transcript is not None and not isinstance(transcript, str):
        raise TypeError('transcript must be text or None')
    if canonical_url:
        parsed = urlsplit(canonical_url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('public HTTP(S) canonical URL required')
    icons = {
        'share-url': '<path d="M6.5 10l3-4M6 11.5l-1 1a3 3 0 01-4-4l3-3a3 3 0 014 0M10 4.5l1-1a3 3 0 014 4l-3 3a3 3 0 01-4 0"/>',
        'copy-minutes': '<rect x="5.5" y="5.5" width="7.5" height="8" rx="1"/><path d="M3 10.5H2.5v-8h8V3"/>',
        'copy-original': '<rect x="6" y="2" width="4" height="7" rx="2"/><path d="M4 7.5a4 4 0 008 0M8 11.5V14M5.5 14h5"/>',
    }
    labels = {'share-url': 'URL 복사하기', 'copy-minutes': '회의록 전체 복사', 'copy-original': '음성 원문 전체 복사'}
    buttons = ''.join(
        f'<button type="button" class="lbtn ghost act" id="{key}"'
        + (' disabled title="음성 전사문이 제공되지 않았습니다"' if key == 'copy-original' and transcript is None else '')
        + f'><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{icons[key]}</svg>{label}</button>'
        for key, label in labels.items()
    )
    help_text = '음성 원문은 받아쓰기 전문입니다.' if transcript is not None else '음성 전사문이 제공되지 않아 원문 복사를 사용할 수 없습니다.'
    bar = f'<div class="hbtns"><p class="action-help">{help_text}</p><div class="meeting-actions" role="group" aria-label="회의록 복사">{buttons}</div></div>'
    data = json.dumps({'url': canonical_url, 'transcript': transcript}, ensure_ascii=False)
    for char, escaped in (('<', '\\u003c'), ('>', '\\u003e'), ('&', '\\u0026')):
        data = data.replace(char, escaped)
    extra = '<p id="action-status" class="share-toast" role="status" aria-live="polite"></p>'
    extra += '<dialog id="copy-dialog" aria-label="복사할 전체 텍스트"><p>자동 복사가 제한됐습니다. 아래 텍스트를 선택해 복사해 주세요.</p><textarea aria-label="복사할 내용" readonly></textarea><button id="close-copy-dialog" type="button">닫기</button></dialog>'
    extra += f'<script type="application/json" id="meeting-copy-data">{data}</script><script>{(ROOT / "minutes-actions.js").read_text()}</script>'
    head = f'<style>{(ROOT / "minutes-actions.css").read_text()}</style>'
    if canonical_url:
        head += f'<link rel="canonical" href="{html.escape(canonical_url, quote=True)}">'
    return page.replace('</header>', bar + '</header>', 1).replace('</head>', head + '</head>', 1).replace('</body>', extra + '</body>', 1)
