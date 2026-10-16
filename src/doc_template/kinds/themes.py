"""문서 디자인 설정 — 배색(doc-template 테마: 츠타야 T1~T6·paper·mono)과 서체를 템플릿에 입힌다.

배색 정본은 이 패키지의 assets/themes/*.json(역할 토큰 bg·panel·line·text·muted·accent·mark·marktext·link).
여기서는 그 토큰을 템플릿 렌더러(C8 토큰)와 doc-template(리서치형) 두 쪽 변수로 함께 내보낸다.
"""
import glob, json, re
from pathlib import Path

C8 = {'name': 'C8 초록', 'note': '흰 바탕 · 먹 · C8 초록', 'light': dict(
    bg='#FFFFFF', panel='#F7F7F8', line='#EAEAED', text='#121212', muted='#6B6B73', accent='#067D14',
    mark='#DCFCE0', marktext='#121212', link='#121212')}
MONO = {'name': '흑백 기본', 'note': '검정과 흰색만', 'light': dict(
    bg='#FFFFFF', panel='#F4F4F4', line='#CFCFCF', text='#000000', muted='#3A3A3A', accent='#000000',
    mark='#E6E6E6', marktext='#000000', link='#000000')}

FONTS = {
    'nanum-square': {'name': '나눔스퀘어', 'note': '네이버 · 문서 서체 확정안(9/23)'},
    'nanum-barun': {'name': '나눔바른고딕', 'note': '네이버 · 비교 후보'},
    'sans': {'name': '고딕', 'note': 'Pretendard — 본문·제목 모두'},
    'serif-head': {'name': '제목 명조', 'note': '제목만 Noto Serif KR, 본문 Pretendard'},
    'serif': {'name': '명조', 'note': '본문까지 Noto Serif KR'},
}
SANS = '"Pretendard Variable",Pretendard,-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif'
SERIF = '"Noto Serif KR","AppleMyungjo","Nanum Myeongjo",serif'
SERIF_LINK = 'https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700;800&display=swap'
# 네이버 나눔 웹폰트 — 원본 그대로 공개 페이지에 올려 둔 파일(FONT-LICENSE 동봉, 9/23 서체 비교·밀도 제안)
_NSQ = 'https://euna-source.github.io/public-pages/doc-density-proposal/'
_NBG = 'https://euna-source.github.io/public-pages/nanum-doc-font-compare/'
NANUM_FACE = {
    'nanum-square': ('NanumSquare', ''.join(
        f'@font-face{{font-family:"NanumSquare";src:url("{_NSQ}NanumSquare{f}.woff") format("woff");font-weight:{w};font-display:swap}}'
        for f, w in (('L', 300), ('R', 400), ('B', 700), ('EB', 800)))),
    'nanum-barun': ('NanumBarunGothicWeb', ''.join(
        f'@font-face{{font-family:"NanumBarunGothicWeb";src:url("{_NBG}{f}") format("woff2");font-weight:{w};font-display:swap}}'
        for f, w in (('NanumBarunGothicWeb.woff2', 400), ('NanumBarunGothicWebBold.woff2', 700)))),
}


def _theme_dir():
    d = Path(__file__).resolve().parent.parent / 'assets' / 'themes'
    return d if d.is_dir() else None


def themes():
    """{id: {name, note, light{...}}} — 흑백 기본이 맨 앞"""
    out = {'mono': MONO, 'c8': C8}
    d = _theme_dir()
    if d:
        for f in sorted(d.glob('*.json')):
            try: j = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError): continue
            nm = j.get('meta', {}).get('name', f.stem)
            out[f.stem] = {'name': nm.split(' · ')[0] if f.stem != 'paper' else '종이·먹', 'note': ' · '.join(nm.split(' · ')[1:]) or nm,
                           'light': j['light']}
    out['mono'] = MONO
    return out


def vars_css(tid):
    """테마 id → 두 렌더러가 함께 쓰는 CSS 변수 선언"""
    t = themes().get(tid or 'mono')
    if not t: return ''
    L = t['light']
    m = {  # C8 템플릿 렌더러 토큰
        '--bg': L['bg'], '--sunken': L['panel'], '--desk': L['panel'], '--line': L['line'], '--line2': L['line'],
        '--fg': L['text'], '--fg2': L['muted'], '--fg3': L['muted'], '--brand': L['accent'], '--brand-ink': L['accent'],
        '--brand-soft': L['mark'], '--mod-ink': L['accent'], '--mod-soft': L['panel'],
        # doc-template(리서치형) 토큰
        '--panel': L['panel'], '--text': L['text'], '--muted': L['muted'], '--accent': L['accent'], '--mark': L['mark'],
        '--marktext': L['marktext'], '--link': L['link'], '--linkline': L['link'], '--obi': L['mark'], '--obitext': L['marktext']}
    return ';'.join(f'{k}:{v}' for k, v in m.items())


def style(theme=None, font=None):
    """문서 <head>에 넣을 조각. 배색 생략은 흑백이며 명시한 배색은 그대로 적용한다."""
    parts, link = [], ''
    theme = 'mono' if theme is None or theme == '' else theme
    if theme:
        parts.append(f':root,:root[data-theme]{{{vars_css(theme)}}}body{{background:var(--bg);color:var(--fg,var(--text))}}')
    if font in ('serif-head', 'serif'):
        link = f'<link rel="stylesheet" href="{SERIF_LINK}">'
        parts.append(f'h1,h2,h3,.mast{{font-family:{SERIF}!important;letter-spacing:0}}')
        if font == 'serif': parts.append(f'body,p,li,td,th{{font-family:{SERIF}!important}}')
    elif font in NANUM_FACE:
        fam, face = NANUM_FACE[font]
        stack = f'"{fam}","Apple SD Gothic Neo",sans-serif'
        parts.append(face + f'body,h1,h2,h3,p,li,td,th,.mast{{font-family:{stack}!important;font-synthesis:none}}:root{{--sans:{stack};--serif:{stack}}}')
    elif font == 'sans':
        parts.append(f'body,h1,h2,h3,p,li,td,th{{font-family:{SANS}!important}}:root{{--serif:{SANS}}}')
    return (link + f'<style id="doc-theme">{"".join(parts)}</style>') if parts else ''


def catalog():
    """모음 페이지 JS에 넣을 목록(선택지·미리보기 적용용)"""
    T = themes()
    return {'themes': [{'id': k, 'name': v['name'], 'note': v['note'], 'sw': [v['light'][x] for x in ('bg', 'accent', 'mark', 'text')], 'css': vars_css(k)} for k, v in T.items()],
            'fonts': [{'id': k, **v} for k, v in FONTS.items()], 'sans': SANS, 'serif': SERIF, 'serifLink': SERIF_LINK,
            'nanum': {k: {'family': v[0], 'face': v[1]} for k, v in NANUM_FACE.items()}}


def monochrome_css(css):
    """CSS 색만 같은 상대 휘도의 회색으로 바꾼다. 본문·URL·그림 파일은 보존한다."""
    def gray(rgb):
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
        y = sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))
        return round(255 * (12.92 * y if y <= .0031308 else 1.055 * y ** (1 / 2.4) - .055))
    def hexcolor(m):
        h = m.group()[1:]
        if len(h) in (3, 4): h = ''.join(c * 2 for c in h)
        g = gray([int(h[i:i+2], 16) / 255 for i in (0, 2, 4)])
        return '#' + f'{g:02x}' * 3 + h[6:]
    def rgbcolor(m):
        parts = [x.strip() for x in m.group(2).split(',')]
        if len(parts) not in (3, 4): return m.group()
        try: rgb = [float(x[:-1]) / 100 if x.endswith('%') else float(x) / 255 for x in parts[:3]]
        except ValueError: return m.group()
        g = gray(rgb)
        return m.group(1) + '(' + ','.join([str(g)] * 3 + parts[3:]) + ')'
    # Only declaration values: selectors, URLs and quoted content are not color tokens.
    def declaration(m):
        value = m.group(2)
        chunks = re.split(r'(url\([^)]*\)|"[^"\n]*"|\'[^\'\n]*\')', value)
        for i in range(0, len(chunks), 2):
            chunks[i] = re.sub(r'#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{4}\b|#[0-9a-fA-F]{3}\b', hexcolor, chunks[i])
            chunks[i] = re.sub(r'\b(rgba?)\(([^)]*)\)', rgbcolor, chunks[i])
        return m.group(1) + ''.join(chunks)
    return re.sub(r'((?:--)?[\w-]+\s*:\s*)([^;{}]+)', declaration, css)


def monochrome_html(html):
    html = re.sub(r'(<style\b[^>]*>)(.*?)(</style>)',
                  lambda m: m[1] + monochrome_css(m[2]) + m[3], html, flags=re.S | re.I)
    return re.sub(r'(\bstyle=)(["\'])(.*?)\2',
                  lambda m: m[1] + m[2] + monochrome_css(m[3]) + m[2], html, flags=re.S | re.I)
