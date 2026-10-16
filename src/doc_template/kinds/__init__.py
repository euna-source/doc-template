"""문서 템플릿 모음의 유형별 렌더러(기획서형 prd·리서치·목록·일정표·회의록·발표) — 스튜디오·모음 페이지가 이 한 곳을 쓴다."""


def call(fn, *args, **kwargs):
    """허용한 함수만 이름으로 부른다 — 스튜디오·모음 페이지가 다른 파이썬에서 `doc-template kinds call`로 쓴다."""
    from . import render as _r, themes as _t, minutes_actions as _m
    table = {'render': _r.render, 'themes': _t.themes, 'fonts': lambda: _t.FONTS, 'catalog': _t.catalog, 'style': _t.style,
             'monochrome_css': _t.monochrome_css, 'monochrome_html': _t.monochrome_html, 'kinds': lambda: list(_r.KINDS), 'attach': _m.attach, 'parse': _r.parse}
    if fn not in table:
        raise ValueError(f'알 수 없는 함수: {fn}')
    return table[fn](*args, **kwargs)
