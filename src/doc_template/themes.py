"""테마 만들기: 팔레트(T1~T6·기본) · 흑백(mono) · 한 가지 색(one:<hex>).
모든 테마는 같은 역할 토큰을 라이트·다크 한 벌로 가진다.
역할: bg panel line text muted accent(절 번호·편집 표식) mark(강조 면) marktext link obi obitext"""
import json
from pathlib import Path
from .color import contrast, fit_contrast, to_oklch, from_oklch

ROOT = Path(__file__).resolve().parent / 'assets'
ROLES = ['bg', 'panel', 'line', 'text', 'muted', 'accent', 'mark', 'marktext', 'link', 'linkline', 'obi', 'obitext']
CHECKS = [('text', 'bg'), ('muted', 'bg'), ('accent', 'bg'), ('link', 'bg'), ('marktext', 'mark'),
          ('text', 'panel'), ('muted', 'panel'), ('obitext', 'obi')]

def _complete(t):
    t = dict(t)
    t.setdefault('obi', t['mark']); t.setdefault('obitext', t['marktext']); t.setdefault('linkline', t['link'])
    return t

def palette(name):
    data = json.loads((ROOT / 'themes' / f'{name}.json').read_text())
    return {m: _complete(data[m]) for m in ('light', 'dark')} | {'meta': data.get('meta', {})}

MONO = {
    'light': dict(bg='#FAFAF8', panel='#F0F0EC', line='#D6D6D1', text='#1A1A1A', muted='#5C5C5C', accent='#1A1A1A',
                  mark='#E4E4E0', marktext='#1A1A1A', link='#1A1A1A', linkline='#1A1A1A', obi='#1A1A1A', obitext='#FAFAF8'),
    'dark': dict(bg='#161716', panel='#1F201E', line='#3D3E3B', text='#ECEBE6', muted='#B4B3AC', accent='#ECEBE6',
                 mark='#45463F', marktext='#FFFFFF', link='#ECEBE6', linkline='#ECEBE6', obi='#ECEBE6', obitext='#161716'),
    'meta': {'name': '흑백', 'note': '색 없이 굵기·밑줄·면 농도로 위계를 만든다. 인쇄·흑백 복사에 그대로 쓴다.'}}

def one_color(hex_, base='mono'):
    """한 가지 색: 바탕·글자는 흑백 모드. 강조색은 절 번호·목차 막대·형광펜·띠지에만 쓰고, 링크는 본문색+흐린 밑줄."""
    L, C, H = to_oklch(hex_)
    out = {'meta': {'name': f'한 가지 색 {hex_.upper()}', 'note': '강조색 하나를 편집 표식(절 번호·목차 막대·형광펜·띠지)에만 쓴다. 링크는 본문색 밑줄.'}}
    for mode in ('light', 'dark'):
        t = dict(MONO[mode])
        if mode == 'light':
            t['mark'] = from_oklch(0.90, min(C, .10), H)
            t['accent'] = fit_contrast(from_oklch(min(L, .55), C, H), t['bg'])
            t['obi'] = hex_.upper()
            t['obitext'] = '#1A1A1A' if contrast('#1A1A1A', hex_) >= contrast('#FFFFFF', hex_) else '#FFFFFF'
        else:
            t['mark'] = from_oklch(max(L, .74), C, H)
            t['marktext'] = t['bg']
            t['accent'] = fit_contrast(from_oklch(max(L, .75), C, H), t['bg'])
            t['obi'] = t['mark']; t['obitext'] = t['bg']
        t['link'] = t['text']; t['linkline'] = t['muted']
        if contrast(t['marktext'], t['mark']) < 4.5:
            t['marktext'] = '#1A1A1A' if contrast('#1A1A1A', t['mark']) > contrast('#FFFFFF', t['mark']) else '#FFFFFF'
        out[mode] = t
    return out

def resolve(spec):
    """spec: 't1'..'t6' · 'paper'(기본) · 'mono' · 'one:#C0381F' · 'one:t1'(그 팔레트의 절 번호색)"""
    if spec == 'mono':
        return MONO
    if spec.startswith('one:'):
        arg = spec[4:]
        if not arg.startswith('#'):
            arg = palette(arg)['light']['accent']
        return one_color(arg)
    return palette(spec)

def audit(theme):
    rows = []
    for mode in ('light', 'dark'):
        t = theme[mode]
        for a, b in CHECKS:
            rows.append((mode, a, b, round(contrast(t[a], t[b]), 2)))
    return rows

def css_vars(theme, mode):
    return ';'.join(f'--{k}:{theme[mode][k]}' for k in ROLES)
