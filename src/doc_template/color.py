"""색 유틸: sRGB↔OKLCH, WCAG 대비, 대비를 맞출 때까지 명도만 움직이는 보정."""
import math

def _lin(c):
    c /= 255
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4

def _unlin(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= .0031308 else 1.055 * c ** (1 / 2.4) - .055

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#' + ''.join('%02X' % max(0, min(255, round(v))) for v in rgb)

def luminance(h):
    r, g, b = (_lin(v) for v in hex_to_rgb(h))
    return .2126 * r + .7152 * g + .0722 * b

def contrast(a, b):
    hi, lo = sorted([luminance(a), luminance(b)], reverse=True)
    return (hi + .05) / (lo + .05)

def to_oklch(h):
    r, g, b = (_lin(v) for v in hex_to_rgb(h))
    l = .4122214708 * r + .5363325363 * g + .0514459929 * b
    m = .2119034982 * r + .6806995451 * g + .1073969566 * b
    s = .0883024619 * r + .2817188376 * g + .6299787005 * b
    l, m, s = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    L = .2104542553 * l + .7936177850 * m - .0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + .4505937099 * s
    B = .0259040371 * l + .7827717662 * m - .8086757660 * s
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360

def from_oklch(L, C, H):
    A, B = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l = (L + .3963377774 * A + .2158037573 * B) ** 3
    m = (L - .1055613458 * A - .0638541728 * B) ** 3
    s = (L - .0894841775 * A - 1.2914855480 * B) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + .2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s
    b = -.0041960863 * l - .7034186147 * m + 1.7076147010 * s
    return rgb_to_hex(tuple(_unlin(v) * 255 for v in (r, g, b)))

def fit_contrast(fg, bg, target=4.5, step=.005):
    """fg의 색상·채도는 두고 명도만 움직여 bg 대비 target 이상으로 만든다(바탕이 어두우면 밝게, 밝으면 어둡게)."""
    if contrast(fg, bg) >= target:
        return fg
    L, C, H = to_oklch(fg)
    direction = 1 if luminance(bg) < .18 else -1
    for _ in range(200):
        L = max(0, min(1, L + direction * step))
        cand = from_oklch(L, C, H)
        if contrast(cand, bg) >= target:
            return cand
    return '#FFFFFF' if direction > 0 else '#000000'
