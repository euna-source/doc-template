from doc_template.render import render
h,_=render('---\ntitle: 테스트\n---\n## 설명 | 설명입니다\n첫 문장입니다.  \n같은 문단의 다음 의미입니다.\n\n새 문단입니다.\n이어 쓰는 문장입니다.\n')
assert '<br class="prose-break"' in h
assert '<p>새 문단입니다.\n이어 쓰는 문장입니다.</p>' in h
assert '@media(max-width:600px){br.prose-break{display:none}}' in h
print('PASS paragraph boundaries and optional mobile break')


def test_front_matter_line_breaks():
    """띠지·덱·띠지 칸의 줄바꿈은 제목처럼 선택적 시각 개행이 되고, 설명(meta description)은 한 줄로 합친다."""
    from doc_template.render import render as _render
    src = ("---\ntitle: 제목\ndeck: |-\n  첫 문장입니다.\n  둘째 문장입니다.\nobi:\n  text: |-\n    결론 하나.\n    결론 둘.\n"
           "  cells:\n    - h: 칸\n      p: |-\n        가\n        나\n---\n## 절 | 결론\n\n본문\n")
    out = _render(src)
    html_out = out[0] if isinstance(out, tuple) else (out.get('html') if isinstance(out, dict) else out)
    assert '결론 하나. <br class="prose-break">결론 둘.' in html_out
    assert '첫 문장입니다. <br class="prose-break">둘째 문장입니다.' in html_out
    assert '가 <br class="prose-break">나' in html_out
    assert 'content="첫 문장입니다. 둘째 문장입니다."' in html_out


if __name__ == '__main__':
    test_front_matter_line_breaks()
    print('PASS front matter line breaks')
